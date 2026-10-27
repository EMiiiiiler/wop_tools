#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padpirate.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Skull Rock Bay" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:0,-2000,900,90,-25" "ship_side:-700,-500,170,-40,-6" "deck:-600,-992,330,0,-10" "hold:-200,-1050,60,20,0" \
  "cabin:-390,-992,160,180,-5" "nest:-90,-992,600,0,-10" "skull:0,150,260,90,8" "skull_in:0,950,60,90,12" "balcony:-60,800,330,290,-5" \
  "crown:0,1088,720,270,-22" "fort:-1150,560,420,135,-15" "court:-1792,1000,120,90,0" "shark:1380,700,380,45,-20" "dive:2112,1312,450,180,-12" \
  "cove:-1300,-150,320,225,-15" "tavern:1280,-640,150,0,0" "tavern_in:1700,-640,120,0,0" "quay:1450,-1850,260,85,-5" "vault:0,-400,-2450,90,0" \
  "slides:-650,950,620,215,-18"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
