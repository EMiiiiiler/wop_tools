#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padcandy.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Candy Garden" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:2050,-1750,1400,135,-24" "falls:700,350,220,90,12" "balcony:0,-1640,470,90,-6" "grove:-850,-650,140,225,2" "pump:-150,250,320,125,4" "yellow:650,-250,170,-35,6" "cave:700,1470,110,90,2" "tree:-1050,350,320,140,10" "fizzy:300,300,-2700,225,12" "summit:-350,1830,1130,-20,-14"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
