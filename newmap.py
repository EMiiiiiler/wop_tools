#!/usr/bin/env python3
"""newmap.py - scaffold a new WoP map folder that already passes the whole pipeline.

    python3 newmap.py wop_padfoo "Pretty Name" [--folder padfoo] [--types "ffa lps team ft syc_ffa"]
                      [--bounds -1536,-1280,1536,1280]

Creates <folder>/ with
    mapinfo.json      names, bounds, arena types, light options, bot test, preview cameras (read by wopbuild.py)
    build_<ns>.py     a small complete generator on woplib (templates/sample/build.py): replace its layout
    README.md         the map's design sheet (fill it in before building: zones, routes, loot, secret)
Then:  python3 wopbuild.py <folder> all
"""
import os, sys, json, argparse, shutil
HERE = os.path.dirname(os.path.abspath(__file__))

README = """# {longname} ({map})

Generator: `wopbuild.py {folder} gen` (or `OUT=<dir> python3 build_{ns}.py`). Full pipeline: `wopbuild.py {folder} all`.

## Design sheet (fill in BEFORE building - see SKILL.md section 1)
- Theme + scale: (e.g. Padman scale ~8u/cm, catalog models at 1.0)
- Playable area: {w} x {h} (good maps are 4000-5000 x 3000-4500; aisles 128-224u)
- Centrepiece (custom MD3):
- 4-8 landmark zones (each enterable AND climbable, roof access by 16u stairs or a pad):
- Routes between zones (every route goes in routes via K.route / stairs16(route=)):
- Loot ladder (hardest spot -> best weapon; Imperius 1600 > Betty/Balloony 1200 > Pumper 1000 > Splasher 900 >
  Boaster 800 > Bubble G 400), 3-6 ammo spots per weapon:
- Water + its exits (16u steps into <= 44u deep water):
- Secret (non-obvious entry -> sealed room: Pad Power, Revival, Killer Ducks; teleporter back):
- Sightline blockers in the open middle band:
- Sounds (sound/world/... that exist):

## Checks
(wopbuild writes report.md in the build folder; paste the summary here when the map ships)
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map'); ap.add_argument('longname')
    ap.add_argument('--folder'); ap.add_argument('--types', default='ffa lps team ft syc_ffa')
    ap.add_argument('--bounds', default='-1536,-1280,1536,1280')
    a = ap.parse_args()
    m = a.map.lower()
    if not m.startswith('wop_'): sys.exit('map names start with wop_ (lower case)')
    ns = m[4:]
    folder = os.path.join(HERE, a.folder or ns)
    if os.path.exists(folder): sys.exit(f'{folder} exists')
    b = [int(v) for v in a.bounds.split(',')]
    os.makedirs(folder)
    info = {
        'map': m, 'ns': ns, 'longname': a.longname, 'generator': f'build_{ns}.py', 'bounds': b,
        'arena_types': a.types,
        'light': {'fast': '-fast -samples 2 -filter', 'final': '-fast -samples 3 -filter -bounce 2 -bouncegrid'},
        'bots': {'gametype': 0, 'minutes': 3, 'bots': 10},
        'sightlines': {'zmax': [64], 'min': 1800, 'target_pct': 4.0},
        'preview': {'title': a.longname, 'texsize': 256, 'bigtex': '',
                    'shots': [f'overview:{b[2] - 200},{b[1] + 200},900,135,-30', f'centre:0,{b[1] + 400},120,90,0',
                              f'north:0,{b[3] - 300},300,270,-10']},
        'levelshots': {'cover': 'overview', 'shots': ['centre', 'north', 'overview']},
    }
    json.dump(info, open(os.path.join(folder, 'mapinfo.json'), 'w'), indent=1)
    shutil.copy(os.path.join(HERE, 'templates', 'sample', 'build.py'), os.path.join(folder, f'build_{ns}.py'))
    open(os.path.join(folder, 'README.md'), 'w').write(README.format(longname=a.longname, map=m, folder=os.path.basename(folder),
                                                                     ns=ns, w=b[2] - b[0], h=b[3] - b[1]))
    print(f'created {folder}: mapinfo.json, build_{ns}.py, README.md\nnext: fill in README.md, then '
          f'python3 wopbuild.py {os.path.basename(folder)} all')


if __name__ == '__main__':
    main()
