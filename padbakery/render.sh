#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padbakery.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Sweet Padman's Bakery" --compact --texsize 192 --bigtex "sign_=1024;street=512;neon_script=512;menu=512;plaque=512" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:1900,-1800,1500,135,-25" "cake:900,-400,500,150,-10" "oven:-900,0,300,180,5" "north:300,800,400,90,0" "mixer:-700,300,600,120,-15" "shop:0,-1950,250,90,5" "shop_k:0,-700,600,270,-20" "cool:1700,-850,200,280,0" "cool_in:1700,-1300,150,300,-5" "racks:-1100,-1300,300,200,0" "bin:-1550,1050,300,135,-5" "caketop:0,-20,700,90,-8" "tunnel:-1300,1728,60,0,0" "vault:0,-420,-1450,90,4" "wallshelf:500,1450,1450,70,-10" "east:1250,300,950,0,-18" "deck:-1700,-320,520,180,-5" "cave:700,300,120,180,0"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
