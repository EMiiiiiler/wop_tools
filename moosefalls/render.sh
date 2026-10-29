#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_moosefalls.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Moose Mountain Falls" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "tree:650,-950,260,122,12" "pool:-650,150,220,140,-12" "grotto:-1250,500,160,118,8" "tower:650,250,320,48,8" "deck:-1900,-1800,300,-15,-15" "igloo:-1250,-2000,90,185,0" "wavepool:-150,-3500,120,180,-4" "bowl:250,-2780,520,-45,-28" "blackhole:450,-4250,300,-35,-8"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
