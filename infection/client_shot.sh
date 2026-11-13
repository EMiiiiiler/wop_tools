#!/bin/bash
# Run the WoP client headless (Xvfb + Mesa llvmpipe) and take screenshots of menus.
# usage: client_shot.sh <wop source dir (wop.x86_64 built with -DBUILD_CLIENT=ON)> <outdir> <client args...>
# example (Create Game menu with Infection selected, mod folder copied next to wop/):
#   client_shot.sh $SRC /tmp/shot +set fs_game infection +set ui_createInfection 1 +wait 150 +ui_creategame +wait 60 +screenshot +wait 20 +quit
# "+set" is applied at start-up; to change the mod at run time use "+game_restart <mod>" (what the Mods menu does).
# The checkout has LFS stubs: one stub image the menu loads is a fatal "LoadTGA" error. Fetch first:
#   lfs_fetch.py $SRC 'wop/menu.pk3dir/**' 'wop/gfx.pk3dir/gfx/**' 'wop/gfx.pk3dir/marks/**' 'wop/gfx.pk3dir/icons/**' \
#     'wop/gfx.pk3dir/hud/**' 'wop/gfx.pk3dir/levelshots/**' 'wop/gfx.pk3dir/sprites/**' 'wop/gfx.pk3dir/spraylogos/**' \
#     'wop/textures.pk3dir/textures/pad_gfx/flare*' 'wop/textures.pk3dir/textures/colors/**' \
#     'wop/textures.pk3dir/textures/pad_gfx02/tinpad*' 'wop/models.pk3dir/models/wop_players/*/icon*' \
#     'wop/models.pk3dir/models/wop_players/*/menu_icon*' 'wop/models.pk3dir/models/wop_players/padman/**' \
#     'wop/music.pk3dir/wopmusic/*/*.tga' 'wop/music.pk3dir/wopmusic/*/*.jpg' 'wop/music.pk3dir/wopmusic/*/*.png'
# The last file opened before an error is printed (strace), which names the next stub to fetch.
SRC=${1:?wop source dir}; O=${2:?outdir}; shift 2
rm -rf "$O"; mkdir -p "$O"; cd "$SRC" || exit 1
LIBGL_ALWAYS_SOFTWARE=1 timeout "${SHOT_TIMEOUT:-150}" strace -f -e trace=openat -o "$O/strace.log" \
  xvfb-run -a -s "-screen 0 1024x768x24" ./wop.x86_64 +set fs_homepath "$O" +set r_fullscreen 0 +set r_mode -1 \
  +set r_customwidth 1024 +set r_customheight 768 +set s_initsound 0 +set com_introplayed 1 +set cl_renderer opengl1 "$@" > "$O/out.log" 2>&1
echo "rc=$?"; grep -n "^ERROR\|Wrote" "$O/out.log" | cut -c1-160 | head -5
grep "pk3dir" "$O/strace.log" | grep -v ENOENT | tail -1 | cut -c1-160
find "$O" -name "*.png"
