#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padarea51.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Area 51: Dreamland" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-2000,-1800,1300,40,-22" "hangar:0,-250,260,90,8" "saucer:-380,820,300,50,4" "cockpit:-120,1150,290,40,-8" "roof:-700,700,900,30,-14" "lab:-1184,380,-400,270,-6" "vault:-1700,300,-420,180,-4" "tower:1200,600,300,30,6" "crash:-500,-1500,250,40,-6" "jet:900,-1500,250,30,-2" "mothership:0,-500,-2420,90,4"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
