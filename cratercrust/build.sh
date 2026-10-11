#!/bin/sh
# Build Crater Crust (v2) and/or Crater Crust Deluxe sources into $OUT (default ./out):
#   OUT=out ./build.sh            both maps
#   OUT=out ./build.sh deluxe     deluxe only
# Writes maps/*.map, textures/, env/, scripts/*.shader, scripts/*.arena (pk3dir layout).
# The checkers run while writing: brush overlaps, model support, item/spawn placement, jump-pad flights, ammo counts.
set -e
H=$(cd "$(dirname "$0")" && pwd); OUT=${OUT:-out}; export OUT
mkdir -p "$OUT/maps" "$OUT/scripts"
WHAT=${1:-both}
if [ "$WHAT" != deluxe ]; then
  python3 "$H/gen_textures.py" "$OUT" > /dev/null
  python3 "$H/gen_shader.py" "$OUT"
  printf '{\n\tmap      "wop_cratercrust"\n\tlonggame "Crater Crust"\n\ttype     "ffa lps team ft ctkd ctl"\n}\n' | sed 's/longgame/longname/' > "$OUT/scripts/wop_cratercrust.arena"
  python3 "$H/check_and_write.py" "$OUT/maps/wop_cratercrust.map" | sed -n '/^brushes/p;/PROBLEMS/,$p'
fi
if [ "$WHAT" != v2 ]; then
  T=$(mktemp -d)
  python3 "$H/gen_textures.py" "$T" > /dev/null && python3 "$H/gen_shader.py" "$T" > /dev/null
  rm -rf "$OUT/textures/ccdeluxe" "$OUT/env/ccdeluxe"; mkdir -p "$OUT/textures" "$OUT/env"
  mv "$T/textures/cratercrust" "$OUT/textures/ccdeluxe"; mv "$T/env/cratercrust" "$OUT/env/ccdeluxe"
  sed 's#cratercrust/#ccdeluxe/#g' "$T/scripts/cratercrust.shader" > "$OUT/scripts/ccdeluxe.shader"; rm -rf "$T"
  python3 "$H/gen_deluxe_textures.py" "$OUT"
  cat >> "$OUT/scripts/ccdeluxe.shader" <<'SH'

// server browser focus pic: cycles the three B shots
levelshots/wop_cratercrust_deluxeB
{
	nomipmaps
	{
		animmap 0.5 levelshots/wop_cratercrust_deluxeB1 levelshots/wop_cratercrust_deluxeB2 levelshots/wop_cratercrust_deluxeB3
	}
}
SH
  printf '{\n\tmap      "wop_cratercrust_deluxe"\n\tlongname "Crater Crust Deluxe"\n\ttype     "ffa lps team ft ctkd ctl"\n}\n' > "$OUT/scripts/wop_cratercrust_deluxe.arena"
  python3 "$H/check_deluxe.py" "$OUT/maps/wop_cratercrust_deluxe.map" | sed -n '/^brushes/p;/PROBLEMS/,$p'
fi
