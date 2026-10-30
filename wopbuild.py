#!/usr/bin/env python3
"""wopbuild.py - one pipeline for every WoP map folder (replaces the per-map compile/check/botrun/render/package .sh).

    python3 wopbuild.py <map folder> <step> [step ...] [--out DIR] [--light fast|final|"<q3map2 -light options>"]

Steps (in pipeline order; aliases: `check` = gen lint compile aas sight, `all` = check bots render levelshots package):
  gen        run the folder's generator (mapinfo.json "generator") with OUT=<out>
  lint       audit_map + lint_map + pad_check (+ mover_sweep when the map has func_bobbing)      [no compiler needed]
  compile    q3map2 BSP -> VIS -> LIGHT, then bspc (always after -light); fails on a leak; reports portals and warnings
  aas        aas_check with the folder's routes.txt (every pickup reachable, no traps, every route both ways)
  sight      sightlines at each mapinfo "sightlines.zmax" level; fails above "target_pct" (default 4 %)
  bots       wopded with bots (mapinfo "bots"), then botreport (every weapon picked up, secret found)
  render     bsp2scene walk-through page (<out>/preview.html, --compact when > 16 MB) + screenshots (<out>/shots/)
  levelshots WoP levelshots from the screenshots (cover + A + animated B1-B3)
  package    <out>/dist/<map>.pk3 + <map>_source.zip, then pk3_check on both
Every run updates <out>/report.json and <out>/report.md (a definition-of-done table: what passed, the key numbers).

Environment: Q3MAP2 (q3map2 binary), BSPC (wopbspc), GAME (dir holding wop/), WOPDED (default $GAME/wopded.x86_64),
THREE (local three.min.js; the published page uses THREEURL, default jsdelivr three@0.158.0),
PLAYWRIGHT_BROWSERS_PATH for screenshots. The build folder is linked into $GAME/wop as zz_<map>.pk3dir.
"""
import os, sys, re, json, time, shutil, subprocess, argparse, zipfile, glob
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ORDER = ['gen', 'lint', 'compile', 'aas', 'sight', 'bots', 'render', 'levelshots', 'package']
ALIASES = {'check': ['gen', 'lint', 'compile', 'aas', 'sight'], 'all': ORDER}


class Build:
    def __init__(self, folder, out, light):
        self.folder = os.path.abspath(folder if os.path.isdir(folder) else os.path.join(HERE, folder))
        self.info = json.load(open(os.path.join(self.folder, 'mapinfo.json')))
        self.map, self.ns = self.info['map'], self.info['ns']
        self.out = os.path.abspath(out or os.environ.get('OUT') or os.path.join(self.folder, 'out'))
        os.makedirs(self.out, exist_ok=True)
        lo = self.info.get('light', {})
        self.light = lo.get(light, light) if light else lo.get('fast', '-fast -samples 2 -filter')
        self.game = os.path.expanduser(os.environ.get('GAME', '~/Games/wop'))
        self.q3map2 = os.environ.get('Q3MAP2', 'q3map2'); self.bspc = os.environ.get('BSPC', 'wopbspc')
        self.rp = os.path.join(self.out, 'report.json')
        self.report = json.load(open(self.rp)) if os.path.exists(self.rp) else {}
        self.mapfile = os.path.join(self.out, 'maps', self.map + '.map')

    # ------------------------------------------------------------------ helpers
    def run(self, cmd, log=None, env=None, timeout=None, cwd=None):
        e = dict(os.environ); e.update(env or {})
        t0 = time.time()
        p = subprocess.run(cmd, cwd=cwd, env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           errors='replace', timeout=timeout)
        if log: open(os.path.join(self.out, log), 'w').write(p.stdout)
        return p.returncode, p.stdout, time.time() - t0

    def shader_dirs(self):
        d = ['--shaders', self.out]
        s = os.path.join(self.game, 'wop', 'scripts.pk3dir')
        if os.path.isdir(s): d += ['--shaders', s]
        return d

    def md3roots(self):
        r = ['--md3root', self.out]
        m = os.path.join(self.game, 'wop', 'models.pk3dir')
        if os.path.isdir(m): r = ['--md3root', m] + r
        return r

    def set(self, step, status, **kw):
        self.report[step] = dict(status=status, time=time.strftime('%Y-%m-%d %H:%M'), **kw)
        icon = {'PASS': 'ok', 'FAIL': 'FAIL', 'WARN': 'warn', 'SKIP': 'skip'}[status]
        print(f'[{step}] {icon} ' + ', '.join(f'{k} {v}' for k, v in kw.items() if k != 'details'))
        self.write_report()
        return status != 'FAIL'

    def write_report(self):
        json.dump(self.report, open(self.rp, 'w'), indent=1)
        rows = []
        for s in ORDER:
            r = self.report.get(s)
            if not r: rows.append(f'| {s} | not run | |'); continue
            info = '; '.join(f'{k}: {v}' for k, v in r.items() if k not in ('status', 'time', 'details'))
            rows.append(f'| {s} | {r["status"]} | {info} |')
        done = all(self.report.get(s, {}).get('status') in ('PASS', 'WARN') for s in ORDER)
        md = (f'# {self.info["longname"]} ({self.map}) - build report\n\n'
              f'Definition of done: every step PASS (WARN = looked at and accepted). **{"DONE" if done else "NOT DONE"}**\n\n'
              '| step | status | numbers |\n|---|---|---|\n' + '\n'.join(rows) + '\n')
        for s in ORDER:
            d = self.report.get(s, {}).get('details')
            if d: md += f'\n## {s}\n```\n{d.strip()[-6000:]}\n```\n'
        open(os.path.join(self.out, 'report.md'), 'w').write(md)

    def link_into_game(self):
        w = os.path.join(self.game, 'wop')
        if not os.path.isdir(w): return False
        link = os.path.join(w, f'zz_{self.map}.pk3dir')
        if os.path.islink(link) and os.readlink(link) != self.out: os.remove(link)
        if not os.path.exists(link): os.symlink(self.out, link)
        sc = os.path.join(self.out, 'scripts', 'custinfoparms.txt')
        if not os.path.exists(sc):
            os.makedirs(os.path.dirname(sc), exist_ok=True)
            shutil.copy(os.path.join(HERE, 'data', 'custinfoparms.txt'), sc)
        return True

    # ------------------------------------------------------------------ steps
    def s_gen(self):
        g = os.path.join(self.folder, self.info.get('generator', f'build_{self.ns}.py'))
        if not os.path.exists(g): return self.set('gen', 'FAIL', details=f'{g} not found (mapinfo.json "generator")')
        md3 = os.path.join(self.game, 'wop', 'models.pk3dir')
        rc, o, t = self.run([PY, '-W', 'error::RuntimeWarning', g], log='gen.log', cwd=self.folder,
                            env={'OUT': self.out, 'MD3ROOT': md3})
        warns = [l.strip() for l in o.splitlines() if 'WARN' in l]
        if rc: return self.set('gen', 'FAIL', seconds=round(t), details=o[-3000:])
        return self.set('gen', 'WARN' if warns else 'PASS', seconds=round(t), warnings=len(warns),
                        details='\n'.join(o.splitlines()[-25:]))

    def s_lint(self):
        sd, mr = self.shader_dirs(), self.md3roots()
        res = {}
        ok = True; det = ''
        for name, cmd in (('audit', [PY, os.path.join(HERE, 'audit_map.py'), self.mapfile] + mr + sd),
                          ('lint', [PY, os.path.join(HERE, 'lint_map.py'), self.mapfile] + mr + sd),
                          ('pads', [PY, os.path.join(HERE, 'pad_check.py'), self.mapfile] + sd)):
            rc, o, t = self.run(cmd, log=f'{name}.log')
            res[name] = 'OK' if rc == 0 else 'FAIL'
            ok &= rc == 0
            det += f'--- {name}\n' + '\n'.join(l for l in o.splitlines() if re.search(r'FAIL|problem|RESULT|BLOCK|short|lands? ', l, re.I))[:3000] + '\n'
        if 'func_bobbing' in open(self.mapfile).read():
            rc, o, t = self.run([PY, os.path.join(HERE, 'mover_sweep.py'), self.mapfile] + sd, log='mover_sweep.log')
            res['mover_sweep'] = 'OK' if rc == 0 else 'FAIL'; ok &= rc == 0
        lw = re.search(r'\((\d+) warnings\)', open(os.path.join(self.out, 'lint.log')).read())
        nw = int(lw.group(1)) if lw else 0
        return self.set('lint', 'PASS' if ok and not nw else ('WARN' if ok else 'FAIL'), lint_warnings=nw, details=det, **res)

    def s_compile(self):
        if not self.link_into_game():
            return self.set('compile', 'FAIL', details=f'GAME={self.game} has no wop/ folder')
        Q = [self.q3map2, '-game', 'quake3', '-fs_basepath', self.game + '/', '-fs_game', 'wop']
        mp = os.path.join('maps', self.map + '.map'); bsp = os.path.join('maps', self.map + '.bsp')
        times = {}
        rc, o, t = self.run(Q + ['-meta', '-custinfoparms', mp], log='bsp.log', cwd=self.out); times['bsp'] = round(t)
        if rc or 'leaked' in o.lower():
            leak = '\n'.join(l for l in o.splitlines() if 'leak' in l.lower() or 'entity' in l.lower())[:2000]
            return self.set('compile', 'FAIL', stage='bsp', details=leak or o[-3000:])
        vfs = f'entering scripts/{self.ns}.shader' in o            # the build folder is in q3map2's VFS
        bad_models = [l for l in o.splitlines() if 'failed loading' in l.lower() or "can't find" in l.lower()]
        dup = sum('Duplicate or Flipped' in l for l in o.splitlines())
        rc, o, t = self.run(Q + ['-vis', '-saveprt', mp], log='vis.log', cwd=self.out); times['vis'] = round(t)
        m = re.search(r'(\d+)\s+numportals', o); portals = int(m.group(1)) if m else -1
        if rc: return self.set('compile', 'FAIL', stage='vis', details=o[-3000:])
        rc, o, t = self.run(Q + ['-light'] + self.light.split() + ['-custinfoparms', mp], log='light.log', cwd=self.out,
                            timeout=4 * 3600)
        times['light'] = round(t)
        if rc: return self.set('compile', 'FAIL', stage='light', details=o[-3000:])
        rc, o, t = self.run([self.bspc, '-forcesidesvisible', '-optimize', '-bsp2aas', bsp], log='bspc.log', cwd=self.out)
        times['bspc'] = round(t)
        if rc or 'leak' in o.lower() or not os.path.exists(os.path.join(self.out, 'maps', self.map + '.aas')):
            return self.set('compile', 'FAIL', stage='bspc', details=o[-3000:])
        reach = re.findall(r'(\d+) total reachability areas', o)
        size = os.path.getsize(os.path.join(self.out, bsp)) / 1e6
        status = 'PASS'
        notes = []
        if bad_models: status = 'FAIL'; notes.append(f'{len(bad_models)} model/shader load failures (VFS paths?)')
        if not vfs:
            status = 'FAIL'; notes.append(f'q3map2 never read scripts/{self.ns}.shader: the build folder is not in its VFS '
                                          f'(link it into <game>/wop as zz_{self.map}.pk3dir) - models/shaders will be missing')
        if portals > 400: status = 'WARN' if status == 'PASS' else status; notes.append('many portals: make more brushes detail')
        if dup: notes.append(f'{dup} "Duplicate or Flipped triangle" (thin rounded parts / coincident pieces)')
        return self.set('compile', status, portals=portals, bsp_mb=round(size, 1), light=self.light, seconds=times,
                        reach_areas=reach[-1] if reach else '?', details='\n'.join(notes + bad_models[:20]))

    def s_aas(self):
        routes = os.path.join(self.folder, 'routes.txt')
        cmd = [PY, os.path.join(HERE, 'aas_check.py'), os.path.join(self.out, 'maps', self.map + '.aas'), self.mapfile]
        if os.path.exists(routes): cmd += ['--route', '@' + routes]
        rc, o, t = self.run(cmd, log='aas.log')
        bad = [l for l in o.splitlines() if re.search(r'NO AREA|UNREACHABLE|TRAP|blocked|NO PATH', l)]
        nr = len([l for l in o.splitlines() if l.strip().startswith('route ')])
        return self.set('aas', 'PASS' if rc == 0 else 'FAIL', routes=nr, problems=len(bad),
                        details='\n'.join(bad[:60]) or '\n'.join(o.splitlines()[-6:]))

    def s_sight(self):
        si = self.info.get('sightlines', {})
        b = ','.join(str(v) for v in self.info['bounds'])
        # level_target_pct {"<zmax>": pct} relaxes the target for upper levels that look across an open atrium (padfridge
        # door bins); the floor level keeps target_pct. status compares each level with its own target.
        target = si.get('target_pct', 4.0); lt = si.get('level_target_pct', {}); worst = 0.0; over = -99.0; det = ''
        for z in si.get('zmax', [64]):
            png = os.path.join(self.out, f'sightlines_{z}.png')
            rc, o, t = self.run([PY, os.path.join(HERE, 'sightlines.py'), self.mapfile, png, f'--bounds={b}', '--zmax', str(z),
                                 '--min', str(si.get('min', 1800)), '--hot', '8'] + self.md3roots() + self.shader_dirs(),
                                log=f'sight_{z}.log')
            m = re.search(r'\(([\d.]+)%\)', o)
            pct = float(m.group(1)) if m else 100.0
            worst = max(worst, pct); over = max(over, pct - float(lt.get(str(z), target)))
            det += f'--- zmax {z}: {pct}% (target {lt.get(str(z), target)})\n' + '\n'.join(o.splitlines()[-10:]) + '\n'
        kw = dict(long_ray_pct=worst, target=target)
        if lt: kw['level_targets'] = ' '.join(f'{k}:{v}' for k, v in lt.items())
        return self.set('sight', 'PASS' if over <= 0 else ('WARN' if over <= 1.5 else 'FAIL'), details=det, **kw)

    def s_bots(self):
        bi = self.info.get('bots', {}); gt, mins, nb = bi.get('gametype', 0), bi.get('minutes', 3), bi.get('bots', 10)
        ded = os.environ.get('WOPDED', os.path.join(self.game, 'wopded.x86_64'))
        if not os.path.exists(ded): return self.set('bots', 'SKIP', details=f'no dedicated server at {ded}')
        self.link_into_game()
        home = os.path.join(self.out, 'botrun'); shutil.rmtree(home, ignore_errors=True); os.makedirs(home)
        cmd = [ded, '+set', 'fs_homepath', home, '+set', 'dedicated', '1', '+set', 'sv_pure', '0', '+set', 'g_gametype', str(gt),
               '+set', 'bot_enable', '1', '+set', 'bot_minplayers', str(nb), '+set', 'g_log', 'games.log', '+set', 'g_logsync', '1',
               '+set', 'timelimit', str(mins), '+set', 'fraglimit', '0', '+set', 'capturelimit', '0', '+map', self.map]
        try:
            # setsid + own session: `pkill -f wopded` from a tool shell kills the shell itself
            subprocess.run(['timeout', str(int(mins * 60 + 45))] + cmd, cwd=os.path.dirname(ded), stdout=open(os.path.join(self.out, 'ded.log'), 'w'),
                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        except Exception as e:
            return self.set('bots', 'FAIL', details=str(e))
        logs = glob.glob(os.path.join(home, '**', 'games.log'), recursive=True)
        if not logs: return self.set('bots', 'FAIL', details=open(os.path.join(self.out, 'ded.log'), errors='replace').read()[-3000:])
        spots = os.path.join(self.out, 'maps', self.map + '.spots.json')
        rc, o, t = self.run([PY, os.path.join(HERE, 'botreport.py'), logs[0], '--map', self.mapfile, '--spots', spots,
                             '--minutes', str(mins), '--bots', str(nb), '--json', os.path.join(self.out, 'bots.json')], log='bots.log')
        k = re.search(r'kills total (\d+)', o)
        w = len(re.findall(r'^WARN', o, re.M))
        return self.set('bots', 'FAIL' if rc else ('WARN' if w else 'PASS'), kills=int(k.group(1)) if k else 0,
                        minutes=mins, bots=nb, details=o)

    def s_render(self):
        pv = self.info.get('preview', {})
        three = os.environ.get('THREE')
        page = os.path.join(self.out, 'preview.html')
        G = os.path.join(self.game, 'wop')
        vfs = []
        for d in ('textures.pk3dir', 'scripts.pk3dir', 'gfx.pk3dir', 'models.pk3dir', 'env.pk3dir'):
            if os.path.isdir(os.path.join(G, d)): vfs += ['--vfs', os.path.join(G, d)]
        vfs += ['--vfs', self.out]
        views = ';'.join(pv.get('shots', []))
        pub = os.path.join(self.out, 'walkthrough.html')

        def base(out):
            b = [PY, os.path.join(HERE, 'preview', 'bsp2scene.py'), os.path.join(self.out, 'maps', self.map + '.bsp'), out] + vfs + \
                ['--title', pv.get('title', self.info['longname']), '--texsize', str(pv.get('texsize', 256))]
            if pv.get('bigtex'): b += ['--bigtex', pv['bigtex']]
            if pv.get('fog'): b += ['--fog', pv['fog']]
            if views: b += ['--views', views]
            return b
        # local page for screenshots (three inlined), published page with the CDN build
        rc, o, t = self.run(base(page) + (['--three', three] if three else []) + ['--compact'], log='render.log')
        if rc: return self.set('render', 'FAIL', details=o[-3000:])
        rc, o2, t2 = self.run(base(pub) + ['--threeurl', os.environ.get('THREEURL', 'https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js'),
                                      '--compact'], log='render_pub.log')
        mb = os.path.getsize(pub) / 1e6 if os.path.exists(pub) else 0
        shots = pv.get('shots', [])
        sdir = os.path.join(self.out, 'shots')
        if three and shots:
            rc, o3, t3 = self.run([PY, os.path.join(HERE, 'preview', 'shoot.py'), page, sdir] + shots, log='shoot.log', timeout=3600)
        n = len(glob.glob(os.path.join(sdir, '*.png')))
        status = 'PASS' if mb and mb <= 16 else 'FAIL'
        return self.set('render', status, walkthrough_mb=round(mb, 1), screenshots=n,
                        details='walkthrough.html is the page to publish (Artifact); look at every screenshot: stairs, '
                                'ceilings, caulk holes, floating models, plain boxes' + ('' if mb <= 16 else
                                '\nover 16 MB: lower preview.texsize / bigtex'))

    def s_levelshots(self):
        ls = self.info.get('levelshots', {})
        sdir = os.path.join(self.out, 'shots')
        cover = os.path.join(sdir, ls.get('cover', 'overview') + '.png')
        if not os.path.exists(cover): return self.set('levelshots', 'FAIL', details=f'{cover} missing: run render first')
        shots = [os.path.join(sdir, s + '.png') for s in ls.get('shots', []) if os.path.exists(os.path.join(sdir, s + '.png'))]
        rc, o, t = self.run([PY, os.path.join(HERE, 'preview', 'levelshots.py'), self.map, os.path.join(self.out, 'levelshots'),
                             '--cover', cover, '--shots'] + shots + ['--title', self.info['longname']], log='levelshots.log')
        n = len(glob.glob(os.path.join(self.out, 'levelshots', '*.jpg')))
        return self.set('levelshots', 'PASS' if rc == 0 and n else 'FAIL', files=n, details=o[-1500:])

    def s_package(self):
        dist = os.path.join(self.out, 'dist'); os.makedirs(dist, exist_ok=True)
        pk3 = os.path.join(dist, self.map + '.pk3'); src = os.path.join(dist, self.map + '_source.zip')
        common = []
        for d in (f'textures/{self.ns}', f'models/{self.ns}', f'env/{self.ns}', f'sound/{self.ns}', 'levelshots'):
            common += [p for p in glob.glob(os.path.join(self.out, d, '**', '*'), recursive=True) if os.path.isfile(p)]
        common += [os.path.join(self.out, 'scripts', self.ns + '.shader'), os.path.join(self.out, 'scripts', self.map + '.arena')]
        bins = [os.path.join(self.out, 'maps', self.map + e) for e in ('.bsp', '.aas')]
        for path, files in ((pk3, bins + common),
                            (src, [self.mapfile, os.path.join(self.out, 'scripts', 'custinfoparms.txt')] + common)):
            if os.path.exists(path): os.remove(path)
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as Z:
                for f in files:
                    if os.path.exists(f): Z.write(f, os.path.relpath(f, self.out))
        cmd = [PY, os.path.join(HERE, 'pk3_check.py'), pk3, '--map', self.map, '--source', src]
        if os.path.isdir(os.path.join(self.game, 'wop')): cmd += ['--game', self.game]
        rc, o, t = self.run(cmd, log='pk3_check.log')
        return self.set('package', 'PASS' if rc == 0 else 'FAIL', pk3_mb=round(os.path.getsize(pk3) / 1e6, 1),
                        source_mb=round(os.path.getsize(src) / 1e6, 1), details=o[-3000:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder'); ap.add_argument('steps', nargs='+')
    ap.add_argument('--out'); ap.add_argument('--light', help='fast | final | "<-light options>" (mapinfo.json "light")')
    ap.add_argument('--keep-going', action='store_true', help='run later steps after a FAIL')
    a = ap.parse_args()
    steps = []
    for s in a.steps: steps += ALIASES.get(s, [s])
    for s in steps:
        if s not in ORDER: sys.exit(f'unknown step {s}; steps: {" ".join(ORDER)} (aliases check, all)')
    B = Build(a.folder, a.out, a.light)
    print(f'{B.map}: out {B.out}')
    ok = True
    for s in steps:
        if not getattr(B, 's_' + s)():
            ok = False
            print(f'see {os.path.join(B.out, "report.md")} and {s}*.log')
            if not a.keep_going: break
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
