#!/bin/sh
# Pack the compiled map: <dist>/wop_moosefalls.pk3 (drop into wop/) and <dist>/wop_moosefalls_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_moosefalls.pk3 $D/wop_moosefalls_source.zip
zip -q -r -X $D/wop_moosefalls.pk3 maps/wop_moosefalls.bsp maps/wop_moosefalls.aas textures/moosefalls models/moosefalls \
  scripts/moosefalls.shader scripts/wop_moosefalls.arena levelshots
zip -q -r -X $D/wop_moosefalls_source.zip maps/wop_moosefalls.map textures/moosefalls models/moosefalls \
  scripts/moosefalls.shader scripts/wop_moosefalls.arena levelshots
ls -la $D
