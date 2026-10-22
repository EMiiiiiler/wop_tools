#!/bin/sh
# Pack the compiled map: <dist>/wop_padbbq.pk3 (drop into wop/) and <dist>/wop_padbbq_source.zip
# (the .map + shader + arena + textures + models for NetRadiant Custom).
# usage: package.sh <workdir> <dist>
W=${1:-./out}; D=${2:-./dist}; mkdir -p $D; D=$(cd $D && pwd)
cd $W || exit 1
rm -f $D/wop_padbbq.pk3 $D/wop_padbbq_source.zip
zip -q -r -X $D/wop_padbbq.pk3 maps/wop_padbbq.bsp maps/wop_padbbq.aas textures/padbbq models/padbbq \
  scripts/padbbq.shader scripts/wop_padbbq.arena levelshots
zip -q -r -X $D/wop_padbbq_source.zip maps/wop_padbbq.map textures/padbbq models/padbbq \
  scripts/padbbq.shader scripts/wop_padbbq.arena levelshots
ls -la $D
