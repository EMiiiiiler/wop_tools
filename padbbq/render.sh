#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padbbq.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Backyard BBQ" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-2150,-1950,1300,40,-22" "grill:-300,200,260,90,-6" "deck:-1200,900,420,70,-4" "pergola:-300,1500,1300,10,-18" \
  "pool:-900,-300,280,140,-14" "shed:-1300,-1200,300,220,-8" "shedin:-1900,-1520,200,250,-8" "kennel:1200,700,260,40,-4" "table:1300,-500,500,270,-16" \
  "lounger:-200,-900,320,200,-12" "vege:1600,-1100,330,60,-10" "cubby:460,-300,300,270,-6" "underdeck:-900,1300,60,80,2" "colony:0,-560,-2460,90,6" \
  "lawn:1900,-1800,300,140,-6" "house:400,0,500,90,6"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
