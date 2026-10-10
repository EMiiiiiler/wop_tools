# wop_tools

Tools for building World of Padman maps with NetRadiant Custom (q3map2) and bspc.

## Map building
- `wopmap.py` - brush/entity library. Brushes are convex hulls of points (boxes, wedges, ramps, n-gon prisms,
  slanted slide segments...), `stairs()` (16u rise, optional thin slabs), `sub_rects()` for cutting holes,
  `sign_box()`/`fit_face()` for exactly-fitted, never-mirrored sign textures, `Map` writer.
- `md3tool.py` - MD3 reader. `python3 md3tool.py bounds <models root> md3bounds.json` rebuilds the bounds table.
- `md3bounds.json` - real bounds of every WoP map object (place models with `origin z = surface - zmin*scale`).
- `waterpark/` - generator for *Splash World: Cloud Lagoon* (`OUT=dir python3 build_waterpark.py`), plus dev
  `compile.sh` / `render.sh`. `textures.py` makes all textures, the shader and the arena.
- `padcounter/build_padcounter.py` - older generator (giant kitchen counter).

## Checks (run on every map)
- `audit_map.py map --md3root <dir holding models/>` - brush overlaps, entities/items/spawns in solids or
  triggers, models resting on a surface (no floating/overhang) and not sunk into brushes, 3-6 ammo per weapon.
- `aas_check.py map.aas map.map` - every pickup reachable by bots from the spawns and not a trap (reads the
  bspc .aas directly; `--points "x,y,z;..."` for extra spots).
- `sightlines.py map out.png` - long eye-level sightlines (brushes + model boxes block), with a top-down plot.
- `check_entities.py` - quick entity-in-solid check (superseded by audit_map).

## Preview
- `preview/bsp2scene.py` - compiled .bsp -> self-contained three.js page (lightmaps, vertex-lit models, sky,
  item markers, camera buttons). `--threeurl` for a CDN build, `--three` to inline a local one.
- `preview/shoot.py` - headless Chromium screenshots of that page from Q3 camera positions.
- `preview/levelshots.py` - WoP-style levelshots (`<map>.jpg` cover, `<map>A.jpg`, animated `<map>B1..B3`).

## q3map2 command notes (NetRadiant Custom, no WoP gamepack)
    q3map2 -game quake3 -fs_basepath "<WoP install dir>/" -fs_game wop -meta -custinfoparms map.map
    q3map2 ... -vis -saveprt map.map
    q3map2 ... -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms map.map
    bspc -forcesidesvisible -optimize -bsp2aas map.bsp        (after -light)
- Separate tokens: `-fs_game wop-fs_basegame wop` is wrong and every misc_model fails to load.
- `-custinfoparms` needs `scripts/custinfoparms.txt` (WoP footstep surfaceparms) in the game folder.

## Building the toolchain on Linux
- NetRadiant-custom 20260114 q3map2 on gcc 13: in `tools/quake3/q3map2/q3map2.h` change the
  `c_bspDrawVert_t0` initialisers `.xyz{ 0 }`, `.st{ 0 }`, `.normal{ 0 }` to `Vector3( 0 )` / `Vector2( 0 )`;
  `make ASSIMP_INTERNAL=yes binaries-q3map2`.
- WoP repo (PadWorld-Entertainment/worldofpadman) builds `wopbspc`, `wopded` and `qagame` with cmake; a
  dedicated server with `+set bot_minplayers 8 +set g_log games.log` is a cheap end-to-end bot test.
- The WoP repo stores assets in LFS; fetch single files from
  `https://media.githubusercontent.com/media/PadWorld-Entertainment/worldofpadman/main/<path>`.
