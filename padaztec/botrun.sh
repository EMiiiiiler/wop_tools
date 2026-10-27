#!/bin/sh
# Bot smoke test on a dedicated server, then a pickup / kill summary of games.log.
# usage: GAME=<dir with wopded + wop/> botrun.sh [gametype (0 = FFA)] [minutes] [bots]
# The map must be visible to the game (symlink the build folder in as wop/zz_padaztec.pk3dir).
G=${GAME:-$HOME/Games/wop}; GT=${1:-0}; MIN=${2:-3}; NB=${3:-10}
H=${BOTHOME:-/tmp/wopbot}; mkdir -p $H; rm -f $H/wop/games.log
cd $G && timeout $((MIN * 60 + 40)) ./wopded.x86_64 +set fs_homepath $H +set dedicated 1 +set sv_pure 0 +set g_gametype $GT \
  +set bot_enable 1 +set bot_minplayers $NB +set g_log games.log +set g_logsync 1 +set timelimit $MIN +set fraglimit 0 \
  +set capturelimit 0 +map wop_padaztec > $H/ded.log 2>&1
L=$H/wop/games.log
echo "== pickups"; grep "Item:" $L | awk '{print $4}' | sort | uniq -c | sort -rn
echo "== kills by means"; grep "Kill:" $L | sed 's/.* by //' | sort | uniq -c | sort -rn
echo "== kills total"; grep -c "Kill:" $L
