#!/bin/sh
# Bot smoke test on a dedicated server, then a pickup / kill summary of games.log.
# usage: GAME=<dir with wopded + wop/> botrun.sh [gametype (8 = CTL, 0 = FFA)] [minutes] [bots]
# The map must be visible to the game (symlink the build folder in as wop/zz_padkitchen.pk3dir).
# If qagame was patched to log "DeathPos: <client> <mod> x y z" (local debug only), deaths are binned by place.
G=${GAME:-$HOME/Games/wop}; GT=${1:-8}; MIN=${2:-3}; NB=${3:-10}
H=${BOTHOME:-/tmp/wopbot}; mkdir -p $H; rm -f $H/wop/games.log
cd $G && timeout $((MIN * 60 + 40)) ./wopded.x86_64 +set fs_homepath $H +set dedicated 1 +set sv_pure 0 +set g_gametype $GT \
  +set bot_enable 1 +set bot_minplayers $NB +set g_log games.log +set g_logsync 1 +set timelimit $MIN +set fraglimit 0 \
  +set capturelimit 0 +map wop_padkitchen > $H/ded.log 2>&1
L=$H/wop/games.log
echo "== pickups"; grep "Item:" $L | awk '{print $4}' | sort | uniq -c | sort -rn
echo "== kills by means"; grep "Kill:" $L | sed 's/.* by //' | sort | uniq -c | sort -rn
echo "== lolly"; grep -cE "Item: [0-9]+ team_CTL_(red|blue)lolly" $L; grep -iE "capture" $L | head
python3 - "$L" <<'EOF'
import sys, collections
mods = collections.Counter(); zones = collections.Counter()
for l in open(sys.argv[1]):
    p = l.split()
    if len(p) > 6 and p[1] == 'DeathPos:':
        mod, x, y, z = int(p[3]), float(p[4]), float(p[5]), float(p[6])
        zone = ('fell' if z < -300 and not (-640 < x < 640 and -1024 < y < -384) else
                'sink' if z < -300 else 'top')
        zones[(zone, mod, round(x / 256) * 256, round(y / 256) * 256)] += 1
for k, v in zones.most_common(25): print('   ', v, k)
EOF
