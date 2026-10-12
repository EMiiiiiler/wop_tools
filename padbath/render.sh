#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...] [--nomarkers]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padbath.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Battle in the Bathtub" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-2500,-1150,1250,30,-28" "redship:-1250,350,420,200,-14" "centre:900,-900,600,140,-16"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
