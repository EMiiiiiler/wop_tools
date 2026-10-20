#!/bin/sh
# usage: GAME=<dir holding wop/*.pk3dir> THREE=three.min.js render.sh <workdir> <outdir> [name:x,y,z,yaw,pitch ...]
W=${1:-./out}; O=${2:-./shots}; shift 2
T=$(dirname "$0")/..; G=${GAME:-$HOME/Games/wop}/wop
python3 $T/preview/bsp2scene.py $W/maps/wop_paddollhouse.bsp $W/preview.html \
  --vfs $G/textures.pk3dir --vfs $G/scripts.pk3dir --vfs $G/gfx.pk3dir --vfs $G/models.pk3dir --vfs $W \
  --three ${THREE:-three.min.js} --title "Padman's Dollhouse" --compact >/dev/null || exit 1
[ $# -eq 0 ] && set -- "overview:-2050,-1900,1500,42,-22" "back:0,-1300,420,90,6" "garden:900,1960,500,205,-14" "kitchen:-640,430,110,85,2" \
  "parlour:640,430,110,95,2" "bathroom:-400,440,450,125,-12" "bedroom:470,450,450,50,-8" "nursery:-460,440,780,125,-6" "library:470,450,780,55,-6" \
  "terrace:0,420,1110,90,4" "attic:-430,420,1110,125,-2" "tower:-120,930,1460,-60,-14" "bed:1500,-700,950,62,-24" "shelf:-1350,-300,800,160,-6" \
  "chest:1040,-1200,330,-90,-14" "tea:-1000,-420,330,-90,-22" "ballroom:0,-520,-2440,90,4" "underbed:1750,-260,70,92,2"
python3 $T/preview/shoot.py $W/preview.html $O "$@"
