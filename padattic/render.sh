#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padattic.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Attic Express" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "flippers:0,-2300,260,90,-10" "midfield:-900,-1500,200,60,-6" "upper:700,400,300,110,-8" \
  "corner:-300,700,420,140,-10" "booth:-500,1100,360,160,-4" "backbox:700,2300,1100,150,-8" "underworld:500,-900,-300,240,-6" "overview:-1150,-2350,1000,62,-28"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
