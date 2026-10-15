#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padshroom.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Shroom Trip" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-1950,-1700,1500,42,-24" "mother:0,-1500,300,90,12" "chamber:-380,-200,1240,40,-5" "plateau:-300,-520,1560,60,-12" "village:-300,250,350,120,6" "stump:-700,-500,500,225,4" "log:300,-700,420,-35,-6" "pond:300,250,350,40,-10" "void:0,-420,-2140,90,8"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
