#!/bin/sh
# Pack the compiled map: <dist>/wop_padpirate.pk3 (drop into wop/) and <dist>/wop_padpirate_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padpirate.pk3 $D/wop_padpirate_source.zip
zip -q -r -X $D/wop_padpirate.pk3 maps/wop_padpirate.bsp maps/wop_padpirate.aas textures/padpirate models/padpirate env/padpirate \
  scripts/padpirate.shader scripts/wop_padpirate.arena levelshots
zip -q -r -X $D/wop_padpirate_source.zip maps/wop_padpirate.map textures/padpirate models/padpirate env/padpirate \
  scripts/padpirate.shader scripts/wop_padpirate.arena scripts/custinfoparms.txt levelshots
ls -la $D
