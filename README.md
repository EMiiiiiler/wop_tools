# wop_tools

Tools for building World of Padman maps with NetRadiant Custom (q3map2) and bspc.

## check_entities.py
Lists entity origins that sit inside a solid world brush (a common cause of
"entity reached from outside" / leak errors in bspc).

    python3 check_entities.py maps/mymap.map

Skips misc_model, and water/trigger/origin/hint/fog brushes. Patches are not tested.
Set `ROOM` at the top to also flag entities outside a bounding box.

## padcounter/build_padcounter.py
Python generator for a whole WoP map project (.map, .shader, .arena, textures, sounds).
Contains reusable helpers: `box`, `prism`, `wedge`, a brush validity check, and a
`MapBuilder` that writes Quake 3 format .map files. `GL` env var scales all misc_model
modelscale values (1.0 = native size). Set `OUT` to the output folder.

## q3map2 command notes (NetRadiant Custom, no WoP gamepack)
Use separate tokens, and check the VFS lines at the top of the log list the wop pk3s:

    q3map2 -v -game quake3 -fs_basepath "<WoP install dir>/" -fs_game wop

- `-fs_game wop-fs_basegame wop` is wrong; it makes q3map2 look for a folder of that name
  and every misc_model fails to load.
- Build the .aas (bspc) after -light, from the final BSP.
- `Unknown surfaceparm: "woodsteps"` is harmless when using -game quake3.
