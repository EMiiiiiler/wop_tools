#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_moosefalls.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Moose Mountain Falls" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-1950,-1600,900,38,-22" "tree:650,-950,260,122,12" "pool:-650,150,220,140,-12" "grotto:-1250,500,160,118,8" "cave:-1720,1260,60,100,0" "tower:650,250,320,48,8" "tiny:520,-1560,260,25,-4" "stump:-640,-420,420,215,-4" "snack:-80,640,160,88,6" "nest:180,-300,500,140,-6"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
