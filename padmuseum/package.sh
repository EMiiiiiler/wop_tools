#!/bin/sh
# Pack the compiled map: <dist>/wop_padmuseum.pk3 (drop into wop/) and <dist>/wop_padmuseum_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padmuseum.pk3 $D/wop_padmuseum_source.zip
zip -q -r -X $D/wop_padmuseum.pk3 maps/wop_padmuseum.bsp maps/wop_padmuseum.aas textures/padmuseum models/padmuseum \
  scripts/padmuseum.shader scripts/wop_padmuseum.arena levelshots
zip -q -r -X $D/wop_padmuseum_source.zip maps/wop_padmuseum.map textures/padmuseum models/padmuseum \
  scripts/padmuseum.shader scripts/wop_padmuseum.arena levelshots
ls -la $D
