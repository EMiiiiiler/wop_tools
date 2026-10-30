---
name: wop-mapping
description: Build World of Padman (WoP) maps for NetRadiant Custom / q3map2 / bspc - the build process, woplib generators, the wopbuild pipeline and its checks, layout, scale, entities, jump pads, movers, water, custom MD3s, shaders, arena files and bot pathing.
---

# World of Padman map building

Distilled from 20+ shipped maps (waterpark, cratercrust, playroom, xmas, padbath, padtank, padpinball, padkitchen,
padattic, padlounge, padshroom, area51, moosefalls, padcandy, padhalloween, paddollhouse, padbbq, padmuseum, padaztec,
padpirate, padspace, padbakery, padgelato). **MUST** rules broke a shipped map when ignored.

Tool repo: https://github.com/EMiiiiiler/wop_tools. Use it; never hand-write .map files. Key pieces:

| Piece | What it does |
|---|---|
| `newmap.py wop_x "Name"` | scaffolds `<ns>/` with `mapinfo.json`, a working generator on woplib, a design-sheet README |
| `wopbuild.py <folder> <steps>` | the pipeline: gen, lint, compile, aas, sight, bots, render, levelshots, package; writes `report.md` |
| `woplib/kit.py` MapKit | placement with occupancy, catalog/custom models + collision, items, pads, secrets, movers, routes, spots.json |
| `woplib/models.py` | custom MD3/IQM + procedural textures + model shader kinds (`configure(ns, out)` once) |
| `woplib/shaders.py` | brush shader stanzas (lm, sky, water, fog, glass, neon, pad, pulse), `.shader` + `.arena` writers (validated) |
| `woplib/padmath.py` | AimAtTarget maths: target placement, flight time, bspc limits |
| `woplib/wopdata.py` | WoP facts: classnames, forbidden items, bot weights, arena tokens, sounds that exist, common shaders |
| `templates/sample/` | the reference generator: hull, house + roof, pool + steps, secret vault, tower pad, cover, loot |
| `tests/run.sh` | regression tests: each rebuilds a bug a shipped map had and checks the checker catches it |

Older map folders (`padbakery/`, `padspace/` ...) are worked examples for special shapes (lathe shells, ships, carved
slabs, solids->MD3). New maps import `woplib`, they don't copy a `*lib.py`.

---

## 1. The process (follow it in order)

**0. Toolchain** (cloud session): start `setup_cloud.sh` in the background first thing (~15 min: q3map2, wopbspc,
wopded, three.js, writes `/root/src/env.sh`). Design and write the generator while it builds. Then
`lfs_fetch.py /root/src/wopsrc --map <out>/maps/X.map` pulls the real catalog MD3s/textures (the clone has LFS stubs;
checks report "LFS stub" until you do).

**1. Design sheet before code.** `newmap.py` writes `<ns>/README.md`; fill it in: theme + scale (section 4), playable
size (4000-5000 x 3000-4500), the centrepiece, 4-8 landmark zones (each enterable AND climbable), the routes between
them, the loot ladder (section 5), water and its exits, the secret, where sightline cover goes, sounds. Ask the user
only about real ambiguity (theme, game types, "keep the old layout?"); otherwise decide and say what you decided.

**2. Build in layers**, each a function in the generator:
1. Structure: one structural hull (or one structural slab with rooms carved out). Everything else detail.
2. Architecture brushes, then `K.reserve()` them and `K.keep_clear()` every door approach, stair foot and landing
   (~96u) BEFORE anything is scattered ("nearest free spot" filled doorways on moosefalls).
3. Main pieces as custom MD3s (`woplib.models`) with `common/weapclip` collision of the same shapes; look at each on a
   contact sheet (`preview/md3sheet.py`) before placing it.
4. Catalog props on real surfaces (`K.catalog`), cover where `sight --hot` says.
5. Items, pads, secret, movers, lights, sounds. `K.fix_items()` last, then `ML.model_shaders()` and write the shader.
   **MUST** register every model shader before the `.shader` file is written (late registrations draw black/grey).

**3. Loop `wopbuild.py <folder> check`** (gen, lint, compile, aas, sight) until every step is PASS. Use the symptom
table (section 2). A WARN is fine only after you looked at it.

**4. `wopbuild.py <folder> bots`**: every weapon picked up, secret found, few environmental deaths. Fix by moving loot,
adding pads from busy routes, botclip strips (section 6).

**5. `wopbuild.py <folder> render levelshots`** and LOOK at every screenshot (Read the PNGs): stairs and ceiling edges,
caulk holes, floating/sunk models, plain boxes that should be props, signs mirrored, rooms too dark/bright. Add camera
shots in `mapinfo.json` for every landmark, inside every building and on every roof.

**6. Final**: `wopbuild.py <folder> compile --light final` then `aas bots render levelshots package` (the .aas must be
rebuilt after the final light). Publish `<out>/walkthrough.html` with the Artifact tool (republish to the same URL for
updates), send `dist/X.pk3` + `dist/X_source.zip`, commit the generator on a branch and open a PR, and save a short
`claude/wop_<map>_notes.md` project note with new lessons.

### Definition of done (`report.md` says DONE)
- gen: generator runs with `-W error::RuntimeWarning`, no kit warnings left unexplained
- lint: `audit_map` RESULT OK, `lint_map` RESULT OK (warnings looked at), `pad_check` every pad lands (t < 2.9 s)
- compile: no leak, q3map2 read the map's shader (build folder in the VFS), no model load failures, portals low
- aas: every pickup reachable from spawns, no TRAP, every route in `routes.txt` works both ways standing
- sight: <= 4 % of eye-level rays over 1800u at every floor level in `mapinfo.json`
- bots: every weapon picked up, secret items taken, environmental deaths < 15 %
- render: walk-through <= 16 MB, screenshots looked at; levelshots made
- package: `pk3_check` OK on the pk3 + source zip (every texture, model surface shader, sound, arena, levelshot)

## 2. Symptom -> cause -> fix

| Symptom (where it shows) | Cause | Fix |
|---|---|---|
| compile: "LEAKED" | a gap in the structural hull, a detail brush used as a seal, or an entity/model origin outside | seal with structural brushes; lint `entities` lists origins outside; rotating mover with an origin key |
| compile: "never read scripts/<ns>.shader" / "failed loading model" | build folder not in q3map2's VFS | wopbuild links it as `<game>/wop/zz_<map>.pk3dir`; `-fs_basepath` and `-fs_game wop` as separate tokens |
| faces untextured in game | `textures/` prefix in the .map, or upper-case names | names `<ns>/name`, lower case (MapKit.write refuses both) |
| giant missing-texture grid | a `common/*` that WoP doesn't have (`common/playerclip`) | `common/clip` is WoP's player clip (lint `names`) |
| see-through holes | caulk on a visible face (lobby side of a wall, jambs, hull sides round a pool hole, sign edges) | lint `caulk` lists them with coordinates; give them a texture (`sign_box(edge=...)`) |
| model draws black / grey | its shader was registered after the .shader was written, or the image is missing | build models first; `ML.check_registry()`; `pk3_check` `models` section |
| alpha leaves render as squares | alpha kind on a .jpg, or alpha >= 128 everywhere | `.tga` with real alpha; translucent plastic = additive glass kind |
| aas: UNREACHABLE pickup | ledge too high (> 18 step / > 33 barrier), 128u gap jump, pad without bspc link | 16u stairs, pad with +60-70 apex, landings away from hurt zones |
| aas: TRAP | pocket you can drop into but not leave (stair flights < 48u apart, 30u corridors) | widen to 48u+, remove the prop, add a fling pad |
| aas route "there blocked" | headroom (step + 56 under a ceiling edge), steps shallower than 30u under a slab | lint `headroom`; open the slab two steps earlier |
| bots: weapon 0 pickups | low bot weight on a pad-only / dead-end spot, or a pad in a cul-de-sac | swap with a heavier weapon, add a pad from a busy route, move it to a busier spot |
| bots: many MOD_FALLING | bots strafe off deadly edges | 24u `K.botclip_edge` strips, flat bridges >= 320 wide, pickups >= 100u from edges |
| bots: MOD_WATER | big low ceilings over water | stand structures on the pool floor or fill water under them with botclip |
| players stuck in water | sheer lip that needs a water jump | lint `water`: 16u steps into <= 44u deep water, or a teleporter |
| item missing at its spot in game | dropped through `common/clip`/botclip/nonsolid at spawn | lint `items`; solid floor or `suspended=True` |
| sight > 4 % | open floors, aligned doorways, spaces under tables/overhangs | props at `sight --hot` cells beside paths; one prop per bay in shelving tunnels |
| "Duplicate or Flipped triangle" | thin rounded parts (r 1), coincident parts, shared railing posts | sharp boxes, dedupe |
| user: "looks boring" / "plain box" | brush blocks for buildings/furniture | custom MD3 + props + lights; the most frequent play-test complaint |
| user: "secret too obvious" | visible entrance | hide it (underwater tunnel, fireplace, coffin, flour bin, drain) |
| aas TRAP on a high shelf/tray whose only drop is > 1000u | bspc traces walk-offs only 1000u down | an exit over a lower drop (botclip gap) or a pad (padfridge freezer) |
| lathe label upside down / mirrored on the contact sheet | revolve() v runs up, image rows run down | flip the image vertically before ML.T (padfridge `reg(lathe=True)`) |
| lint headroom: crouch-only strip along a ramp | the ramp top passes under the edge of the slab beside it | keep the ramp 64u off the slab edge |
| sight FAIL only on upper levels of a vertical map | levels look across an open atrium | cover on shelf fronts + tall props in the atrium; then `level_target_pct` in mapinfo |

## 3. The user's standing rules
- Fill the map with catalog objects (https://worldofpadman.net/en/tutorials/catalog-map-objects/); main pieces
  (centrepieces, buildings, furniture) MUST be custom MD3s, not brush boxes.
- Never place a solid or entity inside another solid or entity (audit_map overlaps + point entities).
- Low portal counts (detail everything but the hull). Models fully on surfaces (no float/overhang).
- Break long sightlines with models (< 4 % of eye rays > 1800u).
- Hard-to-reach spots get the best weapons; 3-6 ammo spots per weapon, some hidden, some in plain sight.
- Every water area has a way out (steps/ramp or teleporter). Full explorability: every door enterable, every building
  climbable, roofs with a clear line of fire (no parapets/clutter).
- Bots must reach everything important (bspc AAS). Include `.shader`, `.arena`, textures, and a phone walk-through.
- Answers are in terms of NetRadiant Custom 20260114, q3map2 `-game quake3 -fs_game wop`, no gamepack.

## 4. Scale

Player box 30 x 30 x 56 (crouch 40), eye +26 over origin (origin = floor + 24), step 18, barrier jump 33.

| Style | Units | Catalog modelscale | Maps |
|---|---|---|---|
| Padman scale (tiny hero, giant room) | ~8 u/cm | 1.0 | playroom, xmas, lounge, shroom, tank, bakery, gelato |
| Backyard toy | ~5 u/cm | 0.6-0.9 | padbbq |
| Army man | ~13 u/cm | 1.3-1.6 | kitchen |
| Dollhouse | ~12 u/cm, doll furniture at 1.5x | - | dollhouse |
| Human 1:4 | 128 u/m | tree 1.0-1.3, bush 0.5, padcar x7 = car | cratercrust |
| Human | 32-64 u/m | tree_summer 0.6, fern 0.25, pad_duck 0.3 | moosefalls, area51, museum, aztec, pirate, space |

Density: aisles 128-224u, rooms only as wide as needed. Check every new prop against something of known size (seat
~17u at human scale) on the contact sheet (a 5 m umbrella happened).

## 5. Entities and loot (woplib.wopdata)
- Weapons `weapon_balloony betty boaster bubbleg imperius pumper splasher` (+ `ammo_*`), `ammo_nipper` (start weapon),
  `marker` orange/green/blue/black/purple. Bot weights: Bubble G 400 < Boaster 800 < Splasher 900 < Pumper 1000 <
  Betty = Balloony 1200 < Imperius 1600. Ladder: Imperius on the hardest spot (summit/roof via pad), Betty/Balloony on
  the next, Bubble G/Boaster in easy busy spots. Bots ignore low-weight weapons on pad-only or dead-end spots.
- Powerups `item_padpower speedy jumper climber visionless revival`; holdables `holdable_floater killerducks boomies
  bambam` (it is `holdable_floater`; `item_floater` does not exist). Armour `item_armor_padshield/shard`.
  No health pickups: `station_health` (origin on the floor, ~92x97 footprint).
- **MUST NOT** place `item_berserker` (server segfault on pickup).
- Spawns `info_player_deathmatch` (origin floor + 25); CTL `team_CTL_redlolly/bluelolly/neutrallolly`,
  `team_redspawn/bluespawn`; CTL is g_gametype 8 and needs a point/mirror-symmetric layout.
- Arena types `ffa lps team ft ctkd ctl 1lc syc_ffa syc_tp bb` (`SH.write_arena` refuses unknown tokens and ctl/1lc
  without lollies). Items: origin floor + 16 (`K.weapon/ammo/item` do it).
- Secret recipe (`K.secret`): non-obvious walk-in entry -> trigger_teleport into a SEALED room below the world (Pad
  Power, Revival, Killer Ducks, armour) + teleporter back; secret_found sound trigger next to (not overlapping) it.

## 6. Bots and bspc
bspc passing a link does not mean bots or players can use it: bot-test.
- **Bots never climb ladders** (bspc strips CONTENTS_LADDER). Stairs: 16u risers, 32u treads (`K.stairs16`); runs of
  32u risers pass the AAS but bots skip them; single 32u crate steps are fine.
- No 128u-gap + 48u-up jumps; plinths in front of items 16u; every reward spot gets a pad even with a scenic climb.
- Traps: keep 48u+ between neighbouring flights, no 30u corridors between props and stairs, a 44u gap in front of a
  stair foot gives no AAS area (keep 48u+).
- Steep cone tiers/skirts give no walk-off links (fling pad per tier); a ramp meeting a roof slab at the same pitch
  leaves a groundless seam (pad); ridge walks 4u proud of the slopes; faceted roofs -> flat terraces; no 45-degree
  bevelled brush touching a ramp.
- Deadly edges: botclip strips, flat bridges >= 320, pickups >= 100u away. trigger_hurt = lava for bspc grown by the
  player box: pad landings > hurt radius + 15 away.
- Water: structures stand on the pool floor (bots drown under big low ceilings) or botclip under them; aas_check
  routes can't start in wadeable water; items on islets 16u above deep water are unreachable.
- Crawl spaces (64u) work (`K.crawl()` to tell lint it is intended). `func_plat` elevators work (`K.elevator`).
- Spiral stairs with ~15-degree treads in a small tower (r < 120) give bspc broken links: add a lift pad.
- Count route use with trigger_multiple -> target_score probes (`AddScore` lines) when a spot gets no visits.

## 7. Jump pads (`K.jumppad`, `woplib.padmath`)
- trigger_push + target_position; AimAtTarget aims from the trigger CENTRE and the target is the APEX. Players keep
  their horizontal speed after the apex, so the target sits at t_up/(t_up+t_down) of the way (kit does it).
- **MUST** keep flight < 2.9 s (bspc predicts ~3 s); >= 20u clearance over edges (pass `edges=`); apex <= ceiling - 40
  under ceilings (pass `ceiling=`). pad_check can pass pads bspc doesn't link: +60-70u apex fixes it.
- bspc lands a pad where the arc first touches ground: fling pads on small tops go on the far side.
- Pad up through a hole = lift (target past the hole edge, high apex). Pad onto a cut-away upper level: stay outside
  the front plane until above slab + 24. Pad into an opening behind a ledge: apex at the opening, <= top - 32.
- Pads off islands need a gap in perimeter clip. Teleport destinations never inside a trigger_push (put them just
  behind it; 400 u/s exit slides the player on). Route endpoints never on a pad.
- Roof access reads better as a pad than a long brush staircase (user preference), but bots still want 16u stairs or a
  pad; both is best.

## 8. Movers
- `misc_model` is static; animated catalog models need `misc_externalmodel` (no modelscale).
- Moving decoration: `K.rotating_model2` / `K.pendulum_model2` (origin brush + tiny nonsolid brush + model2, NO
  origin key; q3map2 adds both -> leak). model2 has no scale. **Never func_bobbing for decoration** (bots ride it).
- Things circling the whole map (fish, UFO, train, duck blimps): one func_rotating at the circle centre with an IQM
  model2 holding every copy (MD3 can't hold geometry beyond +-512u). Ridable train: collision box per car on the
  same func_rotating. **WoP's common/nodraw is NONSOLID**, so collision boxes must be `common/weapclip` or caulk
  (lint warns about all-nodraw brushes).
- func_rotating spawnflags: 4 = X axis, 8 = Y axis, 2 = reverse; keep the swept cylinder clear (lint `rotors`) and
  pickups off movers; rotating pushers never crush.
- func_bobbing ferries for bots: flat hull at deck height, ~256u boat, pier exactly its width, nothing else within
  192u; cabins on a second bobber with identical keys; bobbers instakill pinned players.
- func_plat elevator: drawn raised, `height` = travel, 16u pit for the lowered disc. func_train needs an origin brush.
- Currents: trigger_multiple (wait 0.25-0.5) -> target_push `angles "pitch yaw 0"`; keep zones short, off exits.

## 9. Water, fog, sky, light (woplib.shaders)
- `K.water_box(mn, mx, tex, cutters=[...])`: the whole water recipe (one box, carved, top face drawn, the rest nodraw).
  A shallow puddle standing on a flat floor (<= 24u) passes lint's water check. `SH.slick(name)` = ice (keep it off
  pad landings and deadly edges); `SH.glass(name, shadow=False)` for glass shelves the lights shine through.
- Water: ONE box per body carved by everything inside it (`wopmap.carve`); only top faces get the water shader, the
  rest `<name>_nd` (SH.water writes both). **MUST** have 16u steps or a ramp into <= 44u deep water at an exit.
- Fog "underwater" maps: fog shader on all 6 faces of one brush (`SH.fog`), `q3map_fogDir ( 0 0 -1 )` for a visible top;
  pass `--shaders` to every checker or the fog brush counts as solid.
- Skies: `env/fort-pad512` sunny garden, `env/pf-garden512` night, `env/frost-bite512` snowy evening forest,
  `env/pc-friday-13th-512` night city. Custom cube faces: rt=+x, lf=-x, bk=+y, ft=-y. Indoor maps: sky shader on the
  hull's inner faces so every window shows sky. `q3map_sun` yaw points TO the sun (270 = sun in the south).
- Light: point lights fall off with distance squared: lights ~170u under a 768u ceiling need ~1800-2400 on a 450u grid
  (`K.light_grid`); room lamps ~400 at floor + 150. No `q3map_surfacelight` on shaders of dense MD3s (one emitter per
  triangle). Shaded sides of houses need fill lights.
- Glass: GL_ONE GL_ONE + dim const (`SH.glass`); waterfalls alpha-blended (`flow` kind), never pure additive.
  Neon on a dark backing board. Flames: autosprite2 on single thin quads (`cross_sprites` for merged MD3 surfaces).
- Light compile times: fast `-fast -samples 2 -filter` ~1-3 min; final `-bounce 2 -bouncegrid` 3-110 min (rises with
  lightmapped MD3s and open areas); run long compiles as background tasks.

## 10. Brushes, BSP, portals
- Structural hull/slab only; everything else detail -> 0-35 portals, VIS < 1 s. Seals must be structural.
- Common shaders (wopdata.COMMON): caulk (solid, invisible), weapclip (solid: players + shots), clip (player clip,
  nonsolid for items), botclip, trigger, origin, nodraw (**nonsolid in WoP**), footstep clips (woodclip, sandclip ...).
- misc_model has no collision: weapclip shapes inset a few units (`K.custom(boxes=, cyls=)`, `K.catalog(clip=True)`).
  Food on a plate model floats: thin brush plate. A model's ORIGIN must be inside the world (pad_ducktape's is 34u below
  its base).
- Texture dict keys for brushes: `top`, `bot`, `side`, `n`, `s`, `e`, `w` (MapKit.write refuses faces without one).
- Signs: `sign_box`/`fit_face` (never mirrored); one line on a 4:1 sign; give the edges a texture.
- Carved faces can be far bigger than the room they bound: texture by sampling many points; carve octagons/cylinders
  leaves slivers (drop hull volume < 16); `python3 -W error::RuntimeWarning` catches NaN planes.
- Headroom: the step before a ceiling edge needs step top + 56; railings need clip behind them; every entrance a
  96u clear landing.

## 11. Custom MD3s (woplib.models)
1. `ML.configure(ns, out)`; textures with `ML.T(name, array[, alpha])`; shaders with `ML.S(img, kind, **opt)`.
2. Meshes with meshlib (revolve/lathe, tube, ellipsoid, rbox, prism, disc) or `solids_mesh()` from convex brush solids
   (same solids = the weapclip collision; give those shaders `shade=20-30`). `K.solid_piece(name, brushes, texfn)` does
   both in one call (MD3 stored centred on the footprint, brushes added as weapclip).
3. `ML.save(name, X)` handles MD3 limits (+-512u: tall models stored round mid-height; < 4000 verts per surface;
   collapsed triangles dropped) and records `PLACE[name]` for `K.custom`/`K.prop`. `ML.save_iqm` for movers.
4. Lightmapped by default (`spawnflags 4`, `_castshadows 1`); vertex lit (`lit=False`) for alpha foliage.
5. Contact sheet every model (`preview/md3sheet.py`): broken outlines, floating parts, wrong colours, mirrored text.
- Normals follow the profile direction: a cap profile running outward from the axis faces DOWN (black from above):
  run caps inward or use `inward=True`. Axis swaps must be rotations (det +1). Text on +y quads: u runs +x -> -x;
  on cylinders u increases with the angle. Per-instance colours: misc_model `_remap`. MD3 names unique per variant.
- Animated bits: `deformVertexes move/wave` per surface (lava lamp blobs, fish tails, flies).

## 12. Catalog models
Place by real bounds (`K.model_on` / `K.catalog` use md3bounds.json; bush, cane4, muffin origins are off-centre).
No palm tree (custom). `tree_winter` is leafless (dead indoors). pad_fish/flame_angel face -x, origin at the belly.
waterplant1a/1b (318u) aquarium plants; padstatue_gold (243u) spinning centrepiece; telescope/cabin for dormers.

## 13. Sounds (wopdata.SOUNDS, all verified to exist)
Looped speakers near sources (`K.speaker`), `K.timer_sound` for occasional ones, `K.trigger_sound` for one-shots
(doorbell, applause on a summit). `pk3_check --game` proves every noise exists.

## 14. "Deluxe" features the user likes
Movers (rotating/swinging/orbiting decor), a hidden secret room, an alternative way up (tractor beam, bubble lift,
suction pipe = trigger_push with a glass tube MD3 along `padmath.arc`), ambient + timed + triggered sounds, neon,
animated externalmodels, cloud layer (`SH.sky(cloud=...)`), levelshots, the phone walk-through. "Make it twice as
awesome" went best as a second connected area (balcony, frost deck, wave hall) keeping the old layout.

## 15. Compile commands (what wopbuild runs)
```
q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/X.map
q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/X.map
q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/X.map
bspc -forcesidesvisible -optimize -bsp2aas maps/X.bsp          (MUST run after -light: the checksum changes)
```
`-custinfoparms` needs `scripts/custinfoparms.txt` (wop_tools/data/; "Unknown surfaceparm woodsteps" is harmless).
Install: pk3 (or `zz_X.pk3dir`) directly in a `wop` folder listed by `\path`; "Can't find map" = wrong folder;
Start Server lists filter by game type.

## 16. Cloud-session gotchas
- `pkill -f <name>` from the Bash tool kills the tool's own shell: stop background work with TaskStop or a pid.
- Env vars don't persist between shell calls: `. /root/src/env.sh;` in front of every wopbuild call.
- The shell can't reach cdnjs/npm: three.js comes from the sparse git clone; the published page uses jsdelivr.
- git push needs `add_repo` with push access; `gh pr create` may fail on GraphQL -> `gh api repos/.../pulls`.
- Walk-through over 16 MB: `preview.texsize` 192, smaller `bigtex`, `--compact` (wopbuild always uses it).
