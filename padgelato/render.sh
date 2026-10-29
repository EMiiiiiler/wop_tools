#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padgelato.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Padman's Gelato Parlour" --compact --texsize 192 --bigtex "sign_=1024;street=512;neon_script=512;menu=512;plaque=512" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:1900,-1800,1500,135,-25" "tower:900,-500,500,135,10" "deck:-300,-100,1100,45,-8" "counter:0,900,500,90,-5" "softserve:-1100,-300,600,165,0" "ss_cab:-1500,0,120,180,5" "bar:1100,600,400,0,-5" "glass:700,-200,700,330,-5" "freezer:1800,-700,250,270,0" "fz_in:1450,-1250,200,290,-10" "chest:-1400,-700,400,240,-25" "shop:500,-1100,600,240,-10" "aisle:-1500,1820,100,0,0" "vault:0,-420,-1550,90,8" "shelf:-600,1500,1400,60,-15" "lift:400,-700,300,120,10"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
