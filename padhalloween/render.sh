#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padhalloween.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Pumpkin Hollow" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "gate:0,-2000,260,90,6" "overview:-2050,-1950,1250,42,-24" "manor:0,640,170,90,10" "graveyard:-1000,420,150,120,4" "pumpkin:880,620,170,45,8" "tree:-640,-640,220,35,14" "cottage:-420,-1760,200,150,4" "maze:880,-560,640,-40,-24" "crypt:-1190,1880,-130,180,0" "parlour:-160,1440,100,175,2" "lair:0,-300,-2470,90,12" "roof:420,1330,720,150,-6"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
