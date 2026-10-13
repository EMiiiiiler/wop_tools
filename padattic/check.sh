#!/bin/sh
# Regenerate + compile + audit in one go.
# usage: OUT=<dir> Q3MAP2=... BSPC=... GAME=<dir holding wop/> check.sh [light options]
# OUT must be visible to q3map2 inside the wop folder (symlink it in as zz_padattic.pk3dir).
H=$(cd "$(dirname "$0")" && pwd); O=${OUT:-$H/out}; G=${GAME:-$HOME/Games/wop}
OUT=$O MD3ROOT=$G/wop/models.pk3dir python3 $H/build_padattic.py | grep -E "sweep|SWEEP|brushes" || exit 1
[ -f $O/scripts/custinfoparms.txt ] || echo "note: copy XTRAS/mapping/scripts/custinfoparms.txt to $O/scripts/"
S="--shaders $O --shaders $G/wop/scripts.pk3dir"
python3 $H/../audit_map.py $O/maps/wop_padattic.map --md3root $G/wop/models.pk3dir --md3root $O $S | sed -n '/problem/p;/RESULT/p'
python3 $H/../pad_check.py $O/maps/wop_padattic.map $S | tail -n 1
GAME=$G $H/compile.sh $O ${*:-"-fast -samples 2 -filter"}
grep -i leak $O/bspc.log
python3 $H/../aas_check.py $O/maps/wop_padattic.aas $O/maps/wop_padattic.map --route @$H/routes.txt | grep -v " OK$"
python3 $H/../sightlines.py $O/maps/wop_padattic.map $O/sightlines.png --bounds=-2304,-1792,2304,1792 --min 1800 $S | sed -n 2p
