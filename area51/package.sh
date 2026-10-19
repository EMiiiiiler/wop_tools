#!/bin/sh
# Pack the compiled map: <dist>/wop_padarea51.pk3 (drop into wop/) and <dist>/wop_padarea51_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padarea51.pk3 $D/wop_padarea51_source.zip
zip -q -r -X $D/wop_padarea51.pk3 maps/wop_padarea51.bsp maps/wop_padarea51.aas textures/padarea51 env/padarea51 models/padarea51 \
  scripts/padarea51.shader scripts/wop_padarea51.arena levelshots
zip -q -r -X $D/wop_padarea51_source.zip maps/wop_padarea51.map textures/padarea51 env/padarea51 models/padarea51 \
  scripts/padarea51.shader scripts/wop_padarea51.arena levelshots
ls -la $D
