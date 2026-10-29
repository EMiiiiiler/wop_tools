#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padgelato.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Padman's Gelato Parlour" --compact --texsize 192 --bigtex "sign_=1024;street=512;neon_script=512;menu=512;plaque=512" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:2000,-1900,1600,135,-25" "seating:0,-150,380,270,-8" "counter:0,-700,300,90,0" "kitchen:0,150,850,90,-18" "booths:-1300,-1000,300,180,0" "bar:900,-1000,350,0,0" "softserve:-1000,700,500,170,-5" "vat:-150,450,750,135,-20" "batch:300,250,400,60,0" "freezer:1150,900,250,0,0" "chest:1100,1250,550,30,-20" "aisle:-1380,1810,100,0,0" "vault:0,-420,-1550,90,8" "shelf:-600,1500,1400,60,-15" "deck:-300,-1100,1100,45,-8" "cart:-600,-1300,300,225,-5"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
