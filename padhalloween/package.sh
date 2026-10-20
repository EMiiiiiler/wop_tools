#!/bin/sh
# Pack the compiled map: <dist>/wop_padhalloween.pk3 (drop into wop/) and <dist>/wop_padhalloween_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padhalloween.pk3 $D/wop_padhalloween_source.zip
zip -q -r -X $D/wop_padhalloween.pk3 maps/wop_padhalloween.bsp maps/wop_padhalloween.aas textures/padhalloween models/padhalloween env/padhalloween \
  scripts/padhalloween.shader scripts/wop_padhalloween.arena levelshots
zip -q -r -X $D/wop_padhalloween_source.zip maps/wop_padhalloween.map textures/padhalloween models/padhalloween env/padhalloween \
  scripts/padhalloween.shader scripts/wop_padhalloween.arena levelshots
ls -la $D
