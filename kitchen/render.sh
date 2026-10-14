#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padkitchen.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Countertop Clash" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-2900,-1250,900,30,-22" "toaster:-1900,-1150,260,140,-8" "sink:-700,-150,300,-60,-28" "stove:-900,300,260,30,-6" "island:-1900,-200,180,-40,-6"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
