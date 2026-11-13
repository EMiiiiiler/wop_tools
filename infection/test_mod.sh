#!/bin/bash
# Bot match on the dedicated server with the packaged mod; checks the round flow in games.log.
# usage: test_mod.sh <wop source dir (with wopded.x86_64 built)> [map=wop_backyard] [seconds=200]   (PREP=20 ROUND=60 env vars set the phase lengths)
# Needs dist/infection from build_mod.sh and the map's real .bsp (lfs_fetch.py <src> wop/maps.pk3dir/maps/<map>.bsp).
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?wop source dir}; MAP=${2:-wop_backyard}; SECS=${3:-200}
O=$(mktemp -d); rm -rf "$SRC/infection"; cp -r "$HERE/dist/infection" "$SRC/infection"
# +set on the command line is applied before the cfg runs, so the short phases go into a test cfg
{ cat "$HERE/dist/infection/infection.cfg"; echo "set g_inf_prepTime ${PREP:-20}"; echo "set g_inf_roundTime ${ROUND:-60}"; echo "set timelimit 0"; } > "$SRC/infection/inftest.cfg"
(cd "$SRC" && timeout "$SECS" ./wopded.x86_64 +set fs_homepath "$O" +set dedicated 1 +set sv_pure 0 +set fs_game infection \
  +set g_log games.log +set g_logsync 1 +exec inftest.cfg +map "$MAP" > "$O/ded.log" 2>&1 < /dev/null)
rm -rf "$SRC/infection"
L=$(find "$O" -name games.log | head -1); rc=0
grep -q 'qagame.qvm" found in .*infection' "$O/ded.log" || { echo "FAIL: qagame.qvm not loaded from the mod"; rc=1; }
for k in "InfectionRound: 1 start" "InfectionRelease:" "InfectionRound: 1 end" "InfectionRound: 2 start"; do
  grep -q "$k" "$L" || { echo "FAIL: no '$k' in games.log"; rc=1; }
done
echo "rounds: $(grep -c 'InfectionRound: .* end' "$L")  infected wins: $(grep -c 'infected win' "$L")  survivor wins: $(grep -c 'survivors win' "$L")"
echo "infections: $(grep -c ' Infected: ' "$L")  punchy kills: $(grep -c 'MOD_PUNCHY' "$L")  kills: $(grep -c ' Kill: ' "$L")"
echo "bot errors: $(grep -c 'Error' "$O/ded.log")  log: $L"
# an infected player must never pick up a weapon/ammo/holdable: team is the \t\ field of the last userinfo line
python3 - "$L" <<'PY' || rc=1
import re, sys
team = {}; bad = 0
for line in open(sys.argv[1], errors='replace'):
    m = re.search(r'ClientUserinfoChanged: (\d+) .*?\\t\\(\d)', line)
    if m: team[m.group(1)] = m.group(2); continue
    m = re.search(r' Item: (\d+) (weapon_|ammo_|holdable_)', line)
    if m and team.get(m.group(1)) == '1': bad += 1
print('pickups by infected:', bad)
sys.exit(1 if bad else 0)
PY
[ $rc = 0 ] && echo "RESULT: OK" || echo "RESULT: FAIL"
exit $rc
