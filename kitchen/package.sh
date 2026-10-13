#!/bin/sh
# Pack the compiled map: <dist>/wop_padkitchen.pk3 (drop into wop/) and <dist>/wop_padkitchen_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padkitchen.pk3 $D/wop_padkitchen_source.zip
zip -q -r -X $D/wop_padkitchen.pk3 maps/wop_padkitchen.bsp maps/wop_padkitchen.aas textures/padkitchen models/padkitchen \
  scripts/padkitchen.shader scripts/wop_padkitchen.arena levelshots
zip -q -r -X $D/wop_padkitchen_source.zip maps/wop_padkitchen.map textures/padkitchen models/padkitchen \
  scripts/padkitchen.shader scripts/wop_padkitchen.arena levelshots
ls -la $D
