#!/bin/sh
# Dev compile: BSP -> VIS -> LIGHT -> AAS for a generated waterpark folder.
# usage: Q3MAP2=... BSPC=... GAME=<dir holding wop/> compile.sh <workdir> [light options]
# The workdir must be visible to q3map2 as part of the wop game folder (copy or symlink it in as zz_waterpark.pk3dir).
W=${1:-./out}; shift
LOPT=${*:-"-fast -samples 2"}
Q3MAP2=${Q3MAP2:-q3map2}; BSPC=${BSPC:-wopbspc}; GAME=${GAME:-$HOME/Games/wop}
Q="$Q3MAP2 -game quake3 -fs_basepath $GAME -fs_game wop"
cd "$W" || exit 1
$Q -meta -custinfoparms maps/waterpark.map > bsp.log 2>&1 || { tail bsp.log; exit 1; }
grep -i "leak" bsp.log && exit 1
$Q -vis -saveprt maps/waterpark.map > vis.log 2>&1 || exit 1
$Q -light $LOPT -custinfoparms maps/waterpark.map > light.log 2>&1 || exit 1
$BSPC -forcesidesvisible -optimize -bsp2aas maps/waterpark.bsp > bspc.log 2>&1 || exit 1
grep -E "numportals" vis.log; tail -1 light.log
