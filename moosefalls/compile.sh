#!/bin/sh
# Dev compile: BSP -> VIS -> LIGHT -> AAS for the generated moosefalls map folder.
# usage: Q3MAP2=... BSPC=... GAME=<dir holding wop/> compile.sh <workdir> [light options]
# The workdir must be visible to q3map2 inside the wop game folder (symlink it in as zz_moosefalls.pk3dir)
# and hold scripts/custinfoparms.txt (copy from XTRAS/mapping/scripts in the WoP repo).
W=${1:-./out}; shift
LOPT=${*:-"-fast -samples 2 -filter -bounce 1 -bouncegrid"}
Q3MAP2=${Q3MAP2:-q3map2}; BSPC=${BSPC:-wopbspc}; GAME=${GAME:-$HOME/Games/wop}
N=wop_moosefalls
Q="$Q3MAP2 -game quake3 -fs_basepath $GAME -fs_game wop"
cd "$W" || exit 1
$Q -meta -custinfoparms maps/$N.map > bsp.log 2>&1 || { tail bsp.log; exit 1; }
grep -i "leaked" bsp.log && exit 1
$Q -vis -saveprt maps/$N.map > vis.log 2>&1 || exit 1
$Q -light $LOPT -custinfoparms maps/$N.map > light.log 2>&1 || exit 1
$BSPC -forcesidesvisible -optimize -bsp2aas maps/$N.bsp > bspc.log 2>&1 || exit 1
grep -E "numportals" vis.log; tail -n 1 light.log
