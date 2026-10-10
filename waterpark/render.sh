#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...] [--nomarkers]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/waterpark.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Splash World: Cloud Lagoon" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "sw:-2700,-2700,1500,45,-30" "plaza:0,-1500,90,90,2" "terrace:300,1180,300,110,-12"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
