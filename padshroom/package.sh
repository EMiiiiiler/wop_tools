#!/bin/sh
# Pack the compiled map: <dist>/wop_padshroom.pk3 (drop into wop/) and <dist>/wop_padshroom_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padshroom.pk3 $D/wop_padshroom_source.zip
zip -q -r -X $D/wop_padshroom.pk3 maps/wop_padshroom.bsp maps/wop_padshroom.aas textures/padshroom env/padshroom models/padshroom \
  scripts/padshroom.shader scripts/wop_padshroom.arena levelshots
zip -q -r -X $D/wop_padshroom_source.zip maps/wop_padshroom.map textures/padshroom env/padshroom models/padshroom \
  scripts/padshroom.shader scripts/wop_padshroom.arena levelshots
ls -la $D
