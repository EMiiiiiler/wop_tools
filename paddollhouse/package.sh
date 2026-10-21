#!/bin/sh
# Pack the compiled map: <dist>/wop_paddollhouse.pk3 (drop into wop/) and <dist>/wop_paddollhouse_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_paddollhouse.pk3 $D/wop_paddollhouse_source.zip
zip -q -r -X $D/wop_paddollhouse.pk3 maps/wop_paddollhouse.bsp maps/wop_paddollhouse.aas textures/paddollhouse models/paddollhouse \
  scripts/paddollhouse.shader scripts/wop_paddollhouse.arena levelshots
zip -q -r -X $D/wop_paddollhouse_source.zip maps/wop_paddollhouse.map textures/paddollhouse models/paddollhouse \
  scripts/paddollhouse.shader scripts/wop_paddollhouse.arena levelshots
ls -la $D
