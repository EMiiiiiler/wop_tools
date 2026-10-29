#!/bin/sh
# Pack the compiled map: <dist>/wop_padgelato.pk3 (drop into wop/) and <dist>/wop_padgelato_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padgelato.pk3 $D/wop_padgelato_source.zip
zip -q -r -X $D/wop_padgelato.pk3 maps/wop_padgelato.bsp maps/wop_padgelato.aas textures/padgelato models/padgelato \
  scripts/padgelato.shader scripts/wop_padgelato.arena levelshots
zip -q -r -X $D/wop_padgelato_source.zip maps/wop_padgelato.map textures/padgelato models/padgelato \
  scripts/padgelato.shader scripts/wop_padgelato.arena scripts/custinfoparms.txt levelshots
ls -la $D
