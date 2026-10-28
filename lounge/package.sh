#!/bin/sh
# Pack the compiled map: <dist>/wop_padlounge.pk3 (drop into wop/) and <dist>/wop_padlounge_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padlounge.pk3 $D/wop_padlounge_source.zip
zip -q -r -X $D/wop_padlounge.pk3 maps/wop_padlounge.bsp maps/wop_padlounge.aas textures/padlounge models/padlounge env/padlounge \
  scripts/padlounge.shader scripts/wop_padlounge.arena levelshots
zip -q -r -X $D/wop_padlounge_source.zip maps/wop_padlounge.map textures/padlounge models/padlounge env/padlounge \
  scripts/padlounge.shader scripts/wop_padlounge.arena levelshots
ls -la $D
