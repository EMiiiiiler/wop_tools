#!/bin/sh
# Pack the compiled map: <dist>/wop_padspace.pk3 (drop into wop/) and <dist>/wop_padspace_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padspace.pk3 $D/wop_padspace_source.zip
zip -q -r -X $D/wop_padspace.pk3 maps/wop_padspace.bsp maps/wop_padspace.aas textures/padspace models/padspace env/padspace \
  scripts/padspace.shader scripts/wop_padspace.arena levelshots
zip -q -r -X $D/wop_padspace_source.zip maps/wop_padspace.map textures/padspace models/padspace env/padspace \
  scripts/padspace.shader scripts/wop_padspace.arena scripts/custinfoparms.txt levelshots
ls -la $D
