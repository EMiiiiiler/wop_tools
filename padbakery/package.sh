#!/bin/sh
# Pack the compiled map: <dist>/wop_padbakery.pk3 (drop into wop/) and <dist>/wop_padbakery_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padbakery.pk3 $D/wop_padbakery_source.zip
zip -q -r -X $D/wop_padbakery.pk3 maps/wop_padbakery.bsp maps/wop_padbakery.aas textures/padbakery models/padbakery \
  scripts/padbakery.shader scripts/wop_padbakery.arena levelshots
zip -q -r -X $D/wop_padbakery_source.zip maps/wop_padbakery.map textures/padbakery models/padbakery \
  scripts/padbakery.shader scripts/wop_padbakery.arena scripts/custinfoparms.txt levelshots
ls -la $D
