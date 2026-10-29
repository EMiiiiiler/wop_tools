#!/bin/bash
# Build the map toolchain in a fresh cloud session (no apt): libjpeg-turbo + libxml2 into ~/local,
# NetRadiant Custom 20260114 q3map2, and the WoP repo's wopbspc + wopded (+ qagame).
# usage: setup_cloud.sh [srcdir=/root/src]   (~15 min on 2 cores; run it in the background). Writes <srcdir>/env.sh.
# Result: $S/nrc/install/q3map2.x86_64, $S/wopsrc/wopbspc.x86_64, $S/wopsrc/wopded.x86_64, $S/wopsrc/wop/*.pk3dir
set -x
S=${1:-/root/src}; L=$HOME/local; mkdir -p $S $L; cd $S
J=$(nproc)
[ -f $L/lib/libjpeg.a ] || {
  git clone --depth 1 https://github.com/libjpeg-turbo/libjpeg-turbo.git
  cmake -S libjpeg-turbo -B ljt -DCMAKE_INSTALL_PREFIX=$L -DCMAKE_INSTALL_LIBDIR=lib -DENABLE_SHARED=OFF \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DWITH_TURBOJPEG=OFF && cmake --build ljt -j$J && cmake --install ljt; }
[ -f $L/lib/libxml2.a ] || {
  git clone --depth 1 https://github.com/GNOME/libxml2.git
  cmake -S libxml2 -B lx -DCMAKE_INSTALL_PREFIX=$L -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=OFF \
    -DLIBXML2_WITH_PYTHON=OFF -DLIBXML2_WITH_ICONV=OFF -DLIBXML2_WITH_LZMA=OFF -DLIBXML2_WITH_ZLIB=OFF \
    -DLIBXML2_WITH_ICU=OFF -DLIBXML2_WITH_TESTS=OFF -DLIBXML2_WITH_PROGRAMS=OFF \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON && cmake --build lx -j$J && cmake --install lx; }
[ -x $S/nrc/install/q3map2.x86_64 ] || {
  [ -d nrc ] || git clone --depth 1 -b 20260114 https://github.com/Garux/netradiant-custom.git nrc
  # gcc 13: designated initializer of a Vector3 member
  sed -i -e 's/\.xyz{ 0 }/.xyz = Vector3( 0 )/' -e 's/\.st{ 0 }/.st = Vector2( 0 )/' -e 's/\.normal{ 0 }/.normal = Vector3( 0 )/' \
    nrc/tools/quake3/q3map2/q3map2.h
  XI=$(ls -d $L/include/libxml2)
  make -C nrc -j$J DEPENDENCIES_CHECK=off ASSIMP_INTERNAL=yes BUILD=release \
    CPPFLAGS_JPEG="-I$L/include" LIBS_JPEG="$L/lib/libjpeg.a" \
    CPPFLAGS_XML="-I$XI" LIBS_XML="$L/lib/libxml2.a -lm" binaries-q3map2; }
[ -x $S/wopsrc/wopded.x86_64 ] || {
  [ -d wopsrc ] || GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/PadWorld-Entertainment/worldofpadman.git wopsrc
  cmake -S wopsrc -B wopbuild -DBUILD_CLIENT=OFF -DCMAKE_BUILD_TYPE=Release && cmake --build wopbuild -j$J
  find wopsrc wopbuild -maxdepth 3 \( -name 'wopded*' -o -name 'wopbspc*' -o -name 'qagame*' \) -type f | head; }
ls -la $S/nrc/install/q3map2* $S/wopsrc/wop*.x86_64
# preview + checker dependencies: python libs, three.js r158 (the shell can't reach cdnjs/npm), headless Chromium
python3 -c "import scipy, numpy, PIL" 2>/dev/null || pip install --break-system-packages -q scipy numpy pillow
python3 -c "import playwright" 2>/dev/null || pip install --break-system-packages -q playwright
[ -f $S/three/t/build/three.min.js ] || {
  mkdir -p $S/three && git clone --depth 1 --filter=blob:none --sparse -b r158 https://github.com/mrdoob/three.js.git $S/three/t \
    && git -C $S/three/t sparse-checkout set build; }
cat > $S/env.sh <<EOT
# source this before wopbuild.py
export Q3MAP2=$S/nrc/install/q3map2.x86_64 BSPC=$S/wopsrc/wopbspc.x86_64 GAME=$S/wopsrc WOPDED=$S/wopsrc/wopded.x86_64
export THREE=$S/three/t/build/three.min.js PLAYWRIGHT_BROWSERS_PATH=\${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}
EOT
echo "toolchain ready: . $S/env.sh; then python3 wopbuild.py <map folder> all (lfs_fetch.py $S/wopsrc --map <map> for real models)"
