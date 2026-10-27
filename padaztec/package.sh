#!/bin/sh
# Pack the compiled map: <dist>/wop_padaztec.pk3 (drop into wop/) and <dist>/wop_padaztec_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padaztec.pk3 $D/wop_padaztec_source.zip
zip -q -r -X $D/wop_padaztec.pk3 maps/wop_padaztec.bsp maps/wop_padaztec.aas textures/padaztec models/padaztec env/padaztec \
  scripts/padaztec.shader scripts/wop_padaztec.arena levelshots
zip -q -r -X $D/wop_padaztec_source.zip maps/wop_padaztec.map textures/padaztec models/padaztec env/padaztec \
  scripts/padaztec.shader scripts/wop_padaztec.arena levelshots
ls -la $D
