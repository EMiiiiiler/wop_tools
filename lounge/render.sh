#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padlounge.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Couch Lock" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-1900,-1650,1400,40,-25" "couch:0,300,420,90,-8" "table:-700,-500,560,40,-18" "tent:-500,-900,500,220,-10" "shelf:900,-300,700,15,0"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
