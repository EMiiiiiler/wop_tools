#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_padspace.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Starsplash Station" --compact --bigtex "rocket_skin=1024;sign_=512;vortex=512" >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:0,-2000,1000,90,-28" "lander:-520,-640,280,-35,-14" "rocket_front:0,250,300,90,12" "rocket_in:0,960,70,90,25" \
  "cockpit:-60,1000,420,60,-6" "nose:0,1020,700,90,2" "balcony:-400,980,420,40,-4" "planet:-950,640,420,145,-10" "ring:-1520,1050,360,150,-6" \
  "blackhole:1150,650,520,50,-32" "sat_top:2000,700,460,120,-12" "springs:-1300,-200,320,225,-15" "cafe:1300,-640,160,0,2" "cafe_in:1700,-640,110,0,0" \
  "mc_in:1760,-1504,110,0,0" "boulevard:1450,-1850,260,85,-5" "vault:0,-420,-2440,90,4" "slides:-650,900,640,215,-18" "plaza:600,-200,180,120,4"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
