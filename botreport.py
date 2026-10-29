#!/usr/bin/env python3
"""botreport.py - read a wopded games.log and say what the bots did with the map.

    python3 botreport.py games.log --map maps/X.map [--spots maps/X.spots.json] [--minutes 3] [--bots 10]

Prints pickups per item class (placed vs picked up), kills by means of death, and flags:
  FAIL  a weapon that was never picked up (bots can't reach it, or ignore it: low bot weight on a pad-only / dead-end
        spot - move it, swap it with a higher-weight weapon, or give the spot a second pad from a busy route)
  FAIL  no secret item (Pad Power / Revival / Killer Ducks) taken when the map has a secret
  WARN  falls / drownings / crushes / trigger_hurt deaths (> 15% of deaths: botclip strips along edges, structures in
        water stand on the floor, keep pads away from hurt zones)
  WARN  kill rate outside ~10-40 per minute for 10 bots (empty map, or spawn camping / a tiny map)
Exit 1 when anything FAILs. Run 3-5 minutes with 10 bots for FFA (12-16 on big maps); CTL 5v5 5 minutes.
"""
import os, sys, re, json, argparse
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_map as AM
from woplib import wopdata

ENV_DEATHS = ('MOD_FALLING', 'MOD_WATER', 'MOD_CRUSH', 'MOD_TRIGGER_HURT', 'MOD_LAVA', 'MOD_SLIME', 'MOD_SUICIDE', 'MOD_TELEFRAG')
SECRET_ITEMS = ('item_padpower', 'item_revival', 'holdable_killerducks')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log'); ap.add_argument('--map', required=True); ap.add_argument('--spots')
    ap.add_argument('--minutes', type=float, default=3); ap.add_argument('--bots', type=int, default=10)
    ap.add_argument('--json', help='write the numbers here too')
    a = ap.parse_args()
    lines = open(a.log, errors='ignore').read().splitlines()
    items = Counter(); kills = Counter(); mods = Counter(); scores = Counter()
    for l in lines:
        m = re.search(r'Item: \d+ (\S+)', l)
        if m: items[m.group(1)] += 1; continue
        m = re.search(r'Kill: \d+ \d+ \d+: .* by (\S+)', l)
        if m: mods[m.group(1)] += 1; continue
        if 'AddScore:' in l or 'CTL' in l or 'captured' in l.lower():
            for w in ('Capture', 'capture', 'CAPTURE'):
                if w in l: scores['captures'] += 1; break
    ents = AM.parse(a.map)
    placed = Counter(e['kv'].get('classname') for e in ents)
    spots = json.load(open(a.spots)) if a.spots and os.path.exists(a.spots) else None
    has_secret = bool(spots and spots.get('secrets')) or any(placed.get(c) for c in SECRET_ITEMS)
    fails, warns = [], []
    print('== pickups (placed -> picked up)')
    for c in sorted(set(placed) | set(items)):
        if c not in wopdata.PICKUPS: continue
        flag = ''
        if c.startswith('weapon_') and placed.get(c) and not items.get(c):
            flag = '   <-- never picked up'; fails.append(f'{c} never picked up')
        elif placed.get(c) and not items.get(c) and not c.startswith('ammo_'):
            flag = '   <-- never picked up'
        print(f'   {c:28s} {placed.get(c, 0):3d} -> {items.get(c, 0):4d}{flag}')
    if has_secret and not any(items.get(c) for c in SECRET_ITEMS):
        fails.append('no secret item (Pad Power / Revival / Killer Ducks) picked up: bots never found the secret')
    total = sum(mods.values())
    print('== kills by means of death')
    for m, n in mods.most_common(): print(f'   {m:24s} {n}')
    env = sum(n for m, n in mods.items() if m in ENV_DEATHS)
    print(f'== kills total {total} in {a.minutes:g} min with {a.bots} bots ({total / max(a.minutes, 0.1):.1f}/min)')
    if total and env / total > 0.15:
        warns.append(f'{env} of {total} deaths are environmental ({", ".join(f"{m} {mods[m]}" for m in ENV_DEATHS if mods.get(m))})')
    rate = total / max(a.minutes, 0.1) * 10 / max(a.bots, 1)
    if total and not 10 <= rate <= 40: warns.append(f"kill rate {rate:.1f}/min per 10 bots (expected ~10-40: below = empty map, above = spawn camping or a tiny map)")
    if not total: fails.append('no kills logged: did the server load the map? (check ded.log for "Can\'t find map")')
    if scores: print(f'== CTL captures {scores["captures"]}')
    for w in warns: print('WARN', w)
    for f in fails: print('FAIL', f)
    print('RESULT:', 'OK' if not fails else f'{len(fails)} problem(s)')
    if a.json:
        json.dump(dict(items=items, mods=mods, kills=total, env_deaths=env, fails=fails, warns=warns), open(a.json, 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
