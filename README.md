# wop_tools

Tools for building World of Padman maps with NetRadiant Custom (q3map2) and bspc.

## Map building
- `wopmap.py` - brush/entity library. Brushes are convex hulls of points (boxes, wedges, ramps, n-gon prisms,
  slanted slide segments...), `stairs()` (16u rise, optional thin slabs), `sub_rects()` for cutting holes, `carve()` (CSG: subtract brushes from a brush, e.g. water around everything in it),
  `sign_box()`/`fit_face()` for exactly-fitted, never-mirrored sign textures, `Map` writer.
- `md3write.py` - MD3 writer (one frame, Quake winding, lat/long normals) for custom map objects; `vertex_normals()` helper.
- `md3tool.py` - MD3 reader. `python3 md3tool.py bounds <models root> md3bounds.json` rebuilds the bounds table.
- `md3bounds.json` - real bounds of every WoP map object (place models with `origin z = surface - zmin*scale`).
- `waterpark/` - generator for *Splash World: Cloud Lagoon Deluxe* (`OUT=dir python3 build_waterpark.py`; the Infinity Bar's
  tiki pieces are MD3s from `tiki_models.py`), plus dev
  `compile.sh` / `render.sh`. `textures.py` makes all textures, the shader and the arena.
- `padcounter/build_padcounter.py` - older generator (giant kitchen counter).
- `padtank/` - *Fish Tank Temple* (`wop_padtank`): CTL map in an aquarium, fog-volume water, swimming fish schools on
  func_rotating IQM movers; see padtank/README.md.
- `md3write.py` - minimal MD3 writer for custom map objects (single frame).
- `iqmtool.py` - static IQM writer/reader (float vertices: mover models that reach beyond MD3's +-512 limit).
- `padattic/` - *Attic Express* (`wop_padattic`): a model railway in the attic at night; the train (MD3 parts baked into one
  IQM) circles the table on a func_rotating and can be ridden; mountain tunnel, stations, village, pond trestle, under-table,
  rafter catwalk, dormer window; see padattic/README.md.
- `padpinball/` - *Tilt!* (`wop_padpinball`): Padman inside a giant pinball machine (flippers, pop bumpers and a chrome
  steel ball as MD3 centrepieces, plunger lanes, ramps to corner booths, backbox jackpot room, underworld with the coin box);
  CTL/1LC/FFA, see padpinball/README.md.
- `lounge/` - *Couch Lock* (`wop_padlounge`): FFA in a stoner's living room at night (giant glass bong, lava lamps, hookah,
  cannabis plants as MD3s, grow tent, crawl space under the couch, secret stash shelf); see lounge/README.md.
- `padshroom/` - *Shroom Trip* (`wop_padshroom`): FFA forest floor on a magic-mushroom trip - a hollow golden Mother
  Mushroom with a func_plat elevator to the gill chamber in its cap, fly-agaric cottages, hollow stump, walk-through log,
  rainbow pond, a secret kaleidoscope Void, spores circling on an IQM func_rotating, custom sky cube; see padshroom/README.md.
- `padbath/` - *Battle in the Bathtub* (`wop_padbath`): CTL map, two toy battleships, func_bobbing ferries bots ride; see padbath/README.md.
- `playroom/` - *Padman's Playroom* (`wop_padplayroom`): kid's bedroom at Padman scale, see playroom/README.md.
- `xmas/` - *Padman's Christmas* (`wop_padxmas`): living room on Christmas Eve, climbable tree, fireplace -> roof secret,
  see xmas/README.md.
- `kitchen/` - *Countertop Clash* (`wop_padkitchen`): CTL on a giant kitchen counter (toaster bases, sink, stove, hood
  walkway, fridge-top secret), lots of procedural MD3s (`kitchen_models.py`), see kitchen/README.md.
- `meshlib.py` - mesh helpers for model generators: Mesh (auto winding), revolve (with per-angle radius), tube along a
  path (flat ribbons, twisted UVs), ellipsoid/sphere, rounded and pillowy boxes, prisms (any simple polygon), arc paths,
  and `save_md3()` which shrinks big models to fit MD3's +-512 (returns the modelscale) and drops collapsed triangles.
- `preview/md3sheet.py out.png --vfs <dirs> a.md3 b.md3 ...` - contact sheet of models with their real textures.
- `lfs_fetch.py` - replace LFS stubs in a shallow WoP checkout with the real files; `--map maps/x.map` pulls every md3,
  the images its shaders use (resolved through WoP's shader scripts) and the map's skybox.

## Checks (run on every map)
- `audit_map.py map --md3root <dir holding models/>` - brush overlaps, entities/items/spawns in solids or
  triggers, models resting on a surface (no floating/overhang) and not sunk into brushes, 3-6 ammo per weapon.
- `aas_check.py map.aas map.map` - every pickup reachable by bots from the spawns and not a trap (reads the
  bspc .aas directly; `--points "x,y,z;..."` for extra spots). `--route @routes.txt` checks designed paths
  (stairs, hatches, crate climbs, roofs) work on foot both ways while standing, near the straight line between
  the points, so a back door doesn't hide a blocked front door. `waterpark/routes.txt` is an example.
  With team spawns + lollies it also prints each team's capture run (spawns -> enemy lolly -> home) and the travel types.
  Limit: the AAS sometimes links steps under a low overhang anyway, so still look at stair/ceiling junctions.
- `sightlines.py map out.png` - long eye-level sightlines (brushes + model boxes block), with a top-down plot.
- `pad_check.py map --shaders <dirs>` - flies every jump pad (AimAtTarget velocity, player box, 125 Hz) against the
  solid/clip brushes and reports where it lands or what blocks the arc. bspc is stricter, so still run aas_check.
- `mover_sweep.py map` - every func_bobbing's swept volume (+-height along its axis) must clear the static brushes.
- `check_entities.py` - quick entity-in-solid check (superseded by audit_map).
  audit_map also checks misc_externalmodel support and the Nipper (start weapon) ammo count.

## Preview
- `preview/bsp2scene.py` - compiled .bsp -> self-contained three.js page (lightmaps, vertex-lit models, sky, `--fog`,
  `tcGen environment` stages as smooth sphere-map chrome using the BSP vertex normals,
  func_rotating model2s (MD3 or IQM) spinning live,
  item markers, camera buttons). Brush movers with an origin are put back in place, and mover `model2`s and
  `misc_externalmodel`s (not baked into the bsp) are loaded, func_bobbing movers bob live, from the md3s in the --vfs folders. `--threeurl` for a CDN build, `--three` to inline a local one.
- `preview/shoot.py` - headless Chromium screenshots of that page from Q3 camera positions.
- `preview/md3view.py` - one-MD3 turntable page (parses the real .md3 in the browser; drag/pinch on phones).
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

## Movers and pushers (learned on the waterpark)
- A model that should move without being solid: brush entity with a small `nodraw_ns` brush + `model2`
  (no modelscale for model2). Use `func_pendulum` (rocking) or `func_rotating`; bspc turns every
  `func_bobbing` into a bot "funcbob" platform, even a nonsolid one, so bots try to ride floating ducks.
  Pendulum swing period comes from the brush's depth below the origin; `speed` is the swing in degrees.
- `func_train` needs an origin brush; path_corner origins are where that origin goes.
- Water/slide currents: `trigger_multiple` (wait 0.25-0.5) -> `target_push` with `angles "pitch yaw 0"`
  (pitch > 0 = down) and `speed`; it sets the velocity, so keep zones short and away from exits.
- A jump pad that leaves the island needs a gap in the perimeter clip above rail height.
