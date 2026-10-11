#!/bin/sh
# Regenerate + compile + audit in one go.
# usage: OUT=<dir> Q3MAP2=... BSPC=... GAME=<dir holding wop/> check.sh [light options]
# OUT must be visible to q3map2 inside the wop folder (symlink it in as zz_playroom.pk3dir).
H=$(cd "$(dirname "$0")" && pwd); O=${OUT:-$H/out}; G=${GAME:-$HOME/Games/wop}
OUT=$O python3 $H/build_playroom.py > /dev/null || exit 1
[ -f $O/scripts/custinfoparms.txt ] || echo "note: copy XTRAS/mapping/scripts/custinfoparms.txt to $O/scripts/"
python3 $H/../audit_map.py $O/maps/wop_padplayroom.map --md3root $G/wop/models.pk3dir --shaders $O --shaders $G/wop/scripts.pk3dir | sed -n '/problem/p;/RESULT/p'
GAME=$G $H/compile.sh $O ${*:-"-fast -samples 2 -filter"}
grep -i leak $O/bspc.log
python3 $H/../aas_check.py $O/maps/wop_padplayroom.aas $O/maps/wop_padplayroom.map --route @$H/routes.txt | grep -v " OK$"
python3 $H/../sightlines.py $O/maps/wop_padplayroom.map $O/sightlines.png --bounds=-1792,-1536,1792,1536 | sed -n 2p
