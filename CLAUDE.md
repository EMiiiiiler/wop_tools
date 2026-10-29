# wop_tools

Tools and standing rules for building World of Padman (WoP) maps.

## Setup
- Editor/compiler: NetRadiant Custom (https://github.com/Garux/netradiant-custom/tree/20260114). Give answers in terms of it.
- No WoP gamepack is used. Compile with `-game quake3 -fs_basepath "<WoP install dir>/" -fs_game wop`, as separate tokens. Check the VFS lines at the top of the log list the wop pk3s, or every misc_model fails to load.
- The user often runs q3map2 under Wine (Z: paths), so file name case can matter.
- Bot pathing is built with bspc after `-light`, from the final BSP.

## Map rules
- Use models from https://worldofpadman.net/en/tutorials/catalog-map-objects/ to make maps feel full.
- Always produce a `.shader` and `.arena` file, and include any textures.
- Never place solids or entities inside another entity or solid. Run `check_entities.py` on every generated map.
- Keep portal counts low: make most brushes detail.
- All models must sit fully on a surface, not float or overhang empty space.
- Break up long sightlines with models.
- Put good weapons in hard-to-reach places (top shelf, bottom of the sink).
- Give each weapon 3-6 ammo spots, some hidden and some in plain sight.
- Any water needs a way out (portal, ladder or ramp). Note bots do not climb ladders; use stairs or jump pads.
- Full explorability: every door or building can be entered, and every building can be climbed. Rooftop access must not have geometry blocking line of fire to other players.

## Start here (new map or big change)
- Read `docs/SKILL.md` (the process, definition of done, symptom -> fix table). It is the source of the wop-mapping skill.
- `python3 newmap.py wop_x "Name"` scaffolds a folder on `woplib` (MapKit, models, shaders, padmath, wopdata);
  `templates/sample/build.py` is the reference generator. Don't copy a map's `*lib.py` any more.
- `python3 wopbuild.py <folder> check` (gen lint compile aas sight), then `bots render levelshots package`; every run
  writes `<out>/report.md`. A map is done when every step is PASS (or a WARN you looked at).
- `tests/run.sh` must pass after any change to woplib or a checker.

## Tools (see README.md)
- Fresh cloud session: run `setup_cloud.sh` in the background (~15 min on 2 cores) for q3map2, wopbspc and wopded.
- Generate with `wopmap.py`; place models with `md3bounds.json` so they rest on surfaces.
- In a fresh cloud session, `lfs_fetch.py <wop repo> --map maps/x.map` gets the real md3s/textures/sky the map uses.
- Before delivering any map run: `audit_map.py` (must say RESULT: OK), `pad_check.py` (every pad lands), `aas_check.py` after bspc with a `--route @routes.txt`
  covering every stair/hatch/roof (RESULT: OK),
  `mover_sweep.py` (if the map has func_bobbing), `sightlines.py` (aim for < ~4% of rays over 1800u), then look at it with `preview/bsp2scene.py` + `shoot.py`.
- If wopded is available, run the map with bots and read games.log for pickups/frags.
- `waterpark/` is the reference generator (zones, holes for pools, slides, facades, decoration).

## Known pitfalls
- WoP's `common/nodraw` is NONSOLID (unlike Quake 3). Invisible collision = `common/weapclip` (blocks shots too) or
  `common/caulk`; `common/clip` is the player clip. lint_map warns about all-nodraw brushes on movers/world.
- `item_floater` does not exist (it is `holdable_floater`); `woplib.wopdata.KNOWN_CLASSES` lists what the generators use.
- Every model shader must be registered before the .shader file is written: railings added after (padcandy) got
  `iron_dark_lmrl` with no shader. `pk3_check.py` resolves every MD3/IQM surface shader.
- Texture preview: Q3 texture t runs downward; three.js textures need flipY=false or signs look upside down.
- misc_model is static; animated models need `misc_externalmodel` (no modelscale) with animationStart/End/FPS.
- Moving decoration: nodraw_ns brush + model2 on func_pendulum/func_rotating, not func_bobbing (bots try to ride bobbers).
- Headroom: a ceiling edge over stairs needs step top + 56 below it on the step BEFORE the edge, or players must crouch.
- An item origin must sit 16u above the floor (bbox +-15) or the game drops it as "in solid".
- Probe AAS areas at floor+25 (standing origin); floor+24 sits exactly on the boundary.
- Models only appear in-game if q3map2 baked them in; a "failed loading model" error means the compile command's paths are wrong.
- Pickup classnames should be verified against WoP's entities.def.
- `Unknown surfaceparm: "woodsteps"` is harmless with `-game quake3`.
- A brush entity with an origin brush must NOT also get an `origin` key: q3map2 adds them and the mover ends up
  outside the map (bspc then reports a leak). Give func_rotating/func_train only the origin brush.
- Jump pads: Q3 AimAtTarget aims from the trigger's centre and the target_position is the apex of the arc
  (see `playroom/build_playroom.py` jumppad()).
- Don't place `item_berserker` until WoP fixes g_items.c Pickup_Powerup: it calls G_ForceClientWeapon(ent->client)
  on the item entity (NULL client) and the server segfaults on pickup (found with wopded + gdb on WoP main, Oct 2026).
- misc_model has no collision. Give big models a weapclip box (`playroom/build_playroom.py` solid_mdl()).
- misc_model has no collision for other models either: food on a plate *model* floats; use a thin brush plate.
- Main pieces should be custom MD3s (user rule). Recipe: build the mesh with `meshlib.py`, lightmapped misc_model
  (spawnflags 4, `_castshadows 1`), collision = the old brush shapes as common/weapclip, look at it with
  `preview/md3sheet.py` before placing. `xmas/xmas_models.py` has ~45 examples (furniture, tree, presents, figures).
- `bsp2scene.py --compact` halves the walk-through page (int16 geometry); use it when a map with many MD3s goes over
  the 16 MB artifact limit.
- bspc gives no walk-off links from steep (unwalkable) skirts, so bots get trapped on stacked cone tiers: add an outward
  "fling" jump pad per tier. A ramp meeting a separate roof slab at the same pitch leaves a groundless AAS strip at the
  seam (bots can't walk up): give bots a pad (`xmas/`).
- autosprite2 needs thin quads, taller than wide (flames: 2u slabs, nodraw on the other faces); `alphaGen const`
  replaces the texture's alpha, so don't use it on alpha-cutout sprites (smoke turned into a solid rectangle).
- func_bobbing as a bot ferry (padbath/README.md): bspc links it to grounded areas within 192u of each end outline, using the
  top of the mover's model + 24 as the plane, so the hull entity must be flat at deck height (superstructure = second
  func_bobbing with identical keys). botlib boards only within 16u of the start and gets off within 24u of the end: short
  boat, clear deck centre, dock against a clean pier exactly the boat's width, nothing else within 192u. Bobbers instakill
  anyone they pin (MOD_CRUSH regardless of dmg).
- Bots drown under large low ceilings over water. Either stand the structure on the floor or fill the water under it with
  `common/botclip` (WoP bspc makes botclip solid for the AAS; players still swim through it) - padbath ships float this way.
- A convex brush with 45-degree bevels next to a ramp face left the ramp area ungrounded in bspc (no links); keep ramps
  as plain profiles.
- Water overlapping solids fails audit_map: build one water box and `carve()` it; draw only the surface faces and give the
  internal faces a nodraw water shader (q3map2 only culls exactly coincident faces).
- Fish/creatures that loop round a map: func_rotating + IQM model2 (`iqmtool.py`, `padtank/fish_models.py`); MD3 can't
  hold geometry beyond +-512 of its origin. Fog volumes: run audit_map/sightlines with `--shaders` so the fog brush is
  ignored instead of counted as a solid.
- Bots may skip a long chain of 32u barrier-jump steps even when the AAS links every step; give the reward spot a pad too.
- Custom MD3 buildings (padtank bell): misc_model spawnflags 4 for lightmaps + `_castshadows 1`, collision as invisible
  weapclip brushes of the same shape; pass `--md3root` twice (WoP models + the map folder) to audit_map. The audit's sink
  check now tests real model vertices, so hollow models don't flag scenery inside their bounding box.
- Maps over a deadly drop (counters, islands): bots slip off edges while strafing even though the AAS treats
  `trigger_hurt` as lava. 24u `common/botclip` strips along every exposed edge (gaps where bridges land) keep bot paths
  inside: kitchen bot falls went from 52 to 5 per 3-min match. Keep pickups >= 100u from such edges, and prefer flat
  bridges >= 320 wide (a rounded baguette bridge was a death trap). audit_map/sightlines treat botclip as decor.
- misc_model `angles` follow audit_map.rot_matrix (z' = -sin(pitch) x + ...): pitch -90 turns a model's -x end down
  (catalog pad_fork tines are -x). bsp2scene's coloured octahedra are item markers drawn through walls, not geometry
  (`shoot.py --nomarkers` hides them).
- A misc_model's *origin* must be inside the world too: models whose origin sits far above their base (catalog
  `pad_ducktape`) placed on a low floor put the origin under the map and q3map2 reports "Entity leaked".
- Don't put a misc_teleporter_dest inside a trigger_push (audit flags it); put it just behind the pad: the 400 u/s
  teleport exit speed slides the player onto it.
- `pkill -f wopded` from the Bash tool kills the tool's own shell (its command line contains the pattern); start
  wopded with `setsid nohup ... < /dev/null &` and stop it with its pid or `timeout`.
- bspc predicts jump pad flights for at most ~3 s: a longer flight gets no reachability (bots never use the pad). Keep
  pad_check's `t=` under ~2.9 s.
- Bots skip pickups reached only by long runs of 32u-riser stairs even when aas_check routes pass; use 16u stairs for
  anything bots should climb (attic station roofs). A space enclosed by stair flights and walls with only one-way
  (walk-off) entries is a bot trap: aas_check prints TRAP; keep 48u+ between neighbouring flights.
- A ridable train on a circle: one func_rotating with the origin at the circle centre, nodraw collision boxes per car
  and the whole train as an IQM model2 (padattic). Rotating pushers move riders and anyone in front on their own radius,
  so they never pin players in a tunnel that follows the same circle (func_rotating has no blocked/crush handler).
- `revolve()`/`revolve_grid()` normals follow the profile direction: a cap profile running from the axis outward over the
  top needs `inward=True`, or the cap faces down (invisible from above in game, black lightmap). See padshroom/README.md.
- Round hollow MD3 buildings: `padshroom/build_shroom.py` `ring_seg()`/`stem_shell()` build 16-gon wedge collision with
  doors/windows as skipped wedges, textured by face normal (interior, jambs, caulk under the MD3).
- A `func_plat` (drawn raised, `height` = travel, a 16u pit for the lowered disc) is a bot-usable elevator (bspc elevator
  reachabilities); bots rode a 1176u one in padshroom.
- Bot weapon weights (WoP botfiles/fw_items.c): Bubble G 400 < Boaster 800 < Splasher 900 < Pumper 1000 < Betty/Balloony
  1200 < Imperius 1600. Low-weight weapons on pad-only spots get ignored by bots.
- Rooms carved out of a structural slab (`area51/build_area51.py` ground()): texture each carved face by sampling many
  points across it; a single centroid probe left lab floors and crater slopes as caulk (black holes in game).
- sightlines.py counts custom MD3s only through their weapclip brushes unless you pass `--md3root`; open outdoor maps need real cover in the middle
  band (area51: containers + crate stacks took it from 14.7 % to 4.2 %).
- `meshlib.save_md3` splits surfaces by vertex count (<4000 verts / <8000 tris); dense alpha foliage overflowed the old
  fixed 2600-triangle chunks. Railing runs that share corner posts give q3map2 "Duplicate or Flipped triangle" warnings;
  dedupe posts (moosefalls `gen_railing`).
- Run `sightlines.py` with `--md3root <map folder>` when the cover is custom MD3s, and `--hot N` to see where a blocker helps.
- Catalog `tree_winter` is leafless and reads as a dead tree indoors; moosefalls has a custom `small_pine` MD3 to reuse.
- `carve()` is CSG subtraction; clamping hull vertices to a plane is NOT an intersection. Clip to a half-space with
  `padcandy/build_candy.py` clip_half() or carved ground and water overlap by a unit or two.
- Models floating on water fail the support audit: make them a slow func_rotating model2 (padcandy splash ring).
- Stair railings pass the support audit when an iron stringer plate touches the tread ends (padcandy stairbridge_model).
- aas_check `--route` can't start in wadeable (48u) water: those are swim areas; use the main reachability check.
- Stairs whose steps are shallower than the player box (28u < 30u) always put a standing player over the next step up:
  open a ceiling slab over the stairwell two steps before the step+56 headroom rule says (`padhalloween/hw_houses.stair_e_hole`),
  or aas_check reports the route "there blocked" (walking down still works).
- A faceted sloped roof made of many wedge brushes (pumpkin top) gives bspc ungrounded sliver areas and bots get trapped:
  give the walkable top flat terraces (<= 16u steps) instead (`padhalloween` GP_TERRACES).
- `autosprite2` only works on single quads; misc_model surfaces get merged per shader, so q3map2 warns and the flames break.
  `padhalloween/hwlib.cross_sprites()` turns such quads into crossed quads at save time.
- Don't give `q3map_surfacelight` to shaders on many-triangle MD3s (potion bottles): q3map2 makes emitters per triangle
  (13k lights, slow light). Use point lights; add `q3map_lightSubdivide` to the rest.
- Smooth cut-outs in lathe surfaces (carved pumpkin faces, doors in round walls): `padhalloween/hw_models.carved_shell()`
  (quadtree-refined cells + jambs along the true polygon edges).
- `preview/shoot.py` now waits up to 4 minutes per screenshot (software GL on big outdoor scenes needs > 30 s).
- A flat ridge walk flush with the top edges of two roof slopes got no bspc walk link onto it (route blocked both
  ways); make the ridge walk 4u proud of the slopes (`paddollhouse` house()). Slope brushes clipped at the attic floor
  must leave the gable wall polygon as the eaves moved in by T/tan(pitch) to the ridge underside, or the hull cuts into
  the roof slab.
- Mesh axis swaps for MD3s must be rotations (det +1): a reflection keeps the vertex normals but flips the winding, and
  the faces are culled in game (`paddollhouse/dh_models.RX90`).
- Brush texture names in the .map have no `textures/` prefix (`paddollhouse/wp_hall`); with the prefix q3map2 finds no
  shader/image and the faces render untextured.
- A gable roof drawn as one quad per slope has too few vertices touching the roof brush for the audit's support test:
  build roof shingles as a grid.
- Items drop to the floor at spawn with a MASK_SOLID trace, so a pickup placed on a `common/clip` (playerclip) floor falls
  through it, while bots still route to the original spot. Give such items `spawnflags 1` (suspended) - padbbq pergola.
  Items on a sloping roof need +4u on the slope or the server logs "startsolid" and drops them.
- With `--shaders`, audit_map/pad_check used to class `common/clip` (nonsolid + playerclip) as decoration; it now counts
  as clip, so clip floors stop jump pads in pad_check.
- trigger_hurt becomes lava for bspc, grown by the player box: a jump pad landing within hurt radius + 15 lands in a lava
  area and bots never take it (padbbq grill: hot zone r 48, landing at r 92).
- bspc puts a pad's landing where the arc first touches ground (the near edge of a small top). A fling pad there makes
  the landing area the fling pad's own area and pickups beside it unreachable: put the fling pad on the far side
  (padmuseum dome/geode tops).
- Pads onto tall objects under a low ceiling: pad_check can pass while bspc's flight clips the edge; start the pad
  further back so the arc is high before it crosses the edge, apex <= ceiling - 40 (padmuseum squid tank).
- `skin()`-style wall texturing by face centre needs one wall brush per room (an outer wall spanning three rooms took
  the middle room's wallpaper everywhere).
- Big architecture as MD3 with exact collision: describe it once as convex brush solids (`padaztec/az_shapes.py`), add
  them as `common/weapclip` and turn the same solids into the MD3 with `padaztec/azlib.solids_mesh()` (hidden faces
  culled, texture/UV per face). Give such shaders `q3map_shadeAngle` 20-30 or neighbouring faces get smoothed together.
- `carve()` cutting non-axial shapes (octagons, cylinders) could produce a zero-area sliver face whose plane points are
  collinear (NaN normal, broken brush in the .map); `brush_from_planes` now skips them. Run a build with
  `python3 -W error::RuntimeWarning` to catch new ones.
- Items on a rock islet 16u above deep water are effectively unreachable (Q3 water jump), even if bspc links them.
- A ship hull as collision: convex station prisms (keel to deck) with the rooms carved out (`padpirate/pp_shapes.ship_*`);
  keep the sides vertical above the waterline (CW) and below it use min(visual - 8, CW * plan taper), or the hull pokes
  past jetties built flush to its side. The smooth MD3 skin sits 6+ outside; a cap strip from the skin's top edge in to
  the bulwark's inner face hides the gap (`padpirate/pp_ship.rail_cap`).
- Bots ignored a reward (crow's nest Imperius) reached only by a pad in a cul-de-sac (0 pickups in two runs, one visit in
  4 min) even though bspc linked it; a second pad from a busy route (the jetty) gave 18 pickups. Count route use with
  `DEBUG_TRIG=1 build_pirate.py`: trigger_multiple -> target_score probes log `AddScore: <client> <count> target_score`.
- A 30u corridor between props and stair flights is no corridor for bspc: the crew quarters became a TRAP until the
  capstan in front of the door went.
- `picture()` in the padaztec models used the viewer's left as +u, so every sign/poster on a quad read mirrored; fixed in
  `padpirate/pp_models.picture`.
- Slides leaving a round ring-seg platform: rotate the segments half a step so a flat chord faces the slide and start the
  slide floor ~12u beyond it (no overlap, tiny gap).
- Flat `revolve()` rings/tops drawn with an outward profile face down (black from above): use `inward=True`
  (padspace planet ring). Re-check every flat revolve on a contact sheet from above.
- `carve()` round islets out of octagon pools leaves zero-thickness slivers (q3map2 "duplicate plane"); drop them before
  writing (`padspace/build_space.drop_slivers()`: hull volume < 16 or a face-normal extent < 1).
- `carved_shell()` (padspace/splib) now cuts openings anywhere round the shell (tests u and u +- 2*pi*R); rear windows
  used to be skipped beyond +-108 deg of the face.
- Shell collision openings are whole wedge cells fully inside the polygon: extend window polygons past the layer
  boundaries or pads through the window hit the lintel (padspace nose window).
- Prop placement by occupied volumes (`padbakery/build_bakery.py` FOOT/free()/prop()): reserve every architecture
  brush's bounds before placing props, but never a whole cabinet/room volume, or nothing fits inside it.
- A pad into an opening behind a ledge (oven deck mouth): the arc must peak at the opening (apex <= opening top - 32)
  and stay above ledge + 24 for its last ~120u (`padbakery` p_deck1).
- pad_check can pass pads bspc doesn't link (no reachability, items "UNREACHABLE"): raising the apex 60-70u fixed four
  such pads onto tops in padbakery.
- Alpha cut-out textures whose alpha is >= 128 everywhere render opaque (alphaFunc GE128); use an additive glass shader
  for translucent plastic (strip curtains).
- Open shelving with doorways through the dividers leaks long eye-level sightlines along the tunnel: one prop per bay on
  the doorway line (walk round it) fixes it.
