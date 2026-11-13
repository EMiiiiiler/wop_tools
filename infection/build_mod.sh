#!/bin/bash
# Build the Infection mod (qagame.qvm = the mode, ui.qvm = the Create Game menu entry) from a WoP source checkout.
# usage: build_mod.sh <wop source dir> [build dir] [out dir]
# The patch in src/ was made against the commit in src/WOP_COMMIT; if it no longer applies, rebase it there first.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?wop source dir}; B=${2:-$SRC/../wopbuild}; OUT=${3:-$HERE/dist}
if ! grep -q g_infection.c "$SRC/code/game/CMakeLists.txt"; then
  git -C "$SRC" apply "$HERE/src/infection.patch"
  cp "$HERE/src/g_infection.c" "$SRC/code/game/"
fi
[ -f "$B/CMakeCache.txt" ] || cmake -S "$SRC" -B "$B" -DBUILD_CLIENT=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build "$B" -j"$(nproc)" --target qvm_qagame qvm_ui
rm -rf "$OUT"; mkdir -p "$OUT/infection/pk/vm" "$OUT/infection/pk/src"
cp "$SRC/wop/vm/qagame.qvm" "$SRC/wop/vm/ui.qvm" "$OUT/infection/pk/vm/"
cp "$HERE/src/infection.patch" "$HERE/src/g_infection.c" "$HERE/src/WOP_COMMIT" "$SRC/GPL-2.0.md" "$OUT/infection/pk/src/"
(cd "$OUT/infection/pk" && zip -q -r ../zz_infection.pk3 . && cd .. && rm -rf pk)
cp "$HERE"/mod/*.cfg "$HERE/mod/description.txt" "$HERE/README.md" "$OUT/infection/"
(cd "$OUT" && rm -f wop_infection_mod.zip && zip -q -r wop_infection_mod.zip infection)
ls -la "$OUT" "$OUT/infection"
