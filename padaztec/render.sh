#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padaztec.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Tlaloc's Lagoon" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:0,-2000,1100,90,-25" "summit:-200,200,560,60,-8" "stair:0,-500,120,90,12" "shrine:0,420,520,90,0" \
  "lagoon:-1100,-700,260,300,-14" "sunstone:-500,-1150,120,0,6" "cenote:-1600,1000,120,90,-35" "cenotein:-1600,1300,-200,80,-10" \
  "jaguar:-900,-200,260,140,-10" "cantina:-1100,-1300,200,200,-6" "court:1300,-1250,300,320,-14" "head:1300,1000,250,60,-6" \
  "hall:300,1450,120,110,-2" "tomb:0,560,90,90,-5" "plunge:900,500,300,30,-14" "treasure:0,-450,-2420,90,-4" "slidetop:-200,980,520,180,-12" \
  "flume:600,1000,500,10,-10"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
