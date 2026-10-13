#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padtank.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Fish Tank Temple" --fog "0.16,0.40,0.56,6500" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-2450,-1150,1300,32,-24" "temple:-1250,-420,330,160,-6" "centre:620,-700,560,128,-14" \
  "reef:-500,500,420,135,-8" "bell:-450,-260,330,225,-6"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
