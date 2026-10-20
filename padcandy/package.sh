#!/bin/sh
# Pack the compiled map: <dist>/wop_padcandy.pk3 (drop into wop/) and <dist>/wop_padcandy_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padcandy.pk3 $D/wop_padcandy_source.zip
zip -q -r -X $D/wop_padcandy.pk3 maps/wop_padcandy.bsp maps/wop_padcandy.aas textures/padcandy models/padcandy \
  scripts/padcandy.shader scripts/wop_padcandy.arena levelshots
zip -q -r -X $D/wop_padcandy_source.zip maps/wop_padcandy.map textures/padcandy models/padcandy \
  scripts/padcandy.shader scripts/wop_padcandy.arena levelshots
ls -la $D
