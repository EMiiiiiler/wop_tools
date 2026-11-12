---
name: wop-mapping
description: Build World of Padman (WoP) maps for NetRadiant Custom / q3map2 / bspc - the build process, woplib generators, the wopbuild pipeline and its checks, layout, scale, entities, jump pads, movers, water, custom MD3s, shaders, arena files and bot pathing.
---

# World of Padman map building

Distilled from 20+ shipped maps (waterpark, cratercrust, playroom, xmas, padbath, padtank, padpinball, padkitchen,
padattic, padlounge, padshroom, area51, moosefalls, padcandy, padhalloween, paddollhouse, padbbq, padmuseum, padaztec,
padpirate, padspace, padbakery, padgelato, padgarage). **MUST** rules broke a shipped map when ignored.

Tool repo: https://github.com/EMiiiiiler/wop_tools. Use it; never hand-write .map files. The repo's `docs/SKILL.md` is
the source of this skill. Key pieces:

| Piece | What it does |
|---|---|
| `newmap.py wop_x "Name"` | scaffolds `<ns>/` with `mapinfo.json`, a working generator on woplib, a design-sheet README |
| `wopbuild.py <folder> <steps>` | the pipeline: gen, lint, compile, aas, sight, bots, render, levelshots, package; writes `report.md`. `preview` (= gen + quick) is the ~20 s unlit walk-through for review rounds |
| `woplib/kit.py` MapKit | placement with occupancy, catalog/custom models + collision, items, pads, secrets, movers, routes, spots.json |
| `woplib/models.py` | custom MD3/IQM + procedural textures + model shader kinds (`configure(ns, out)` once) |
| `woplib/shaders.py` | brush shader stanzas (lm, sky, water, fog, glass, neon, pad, pulse, slick), `.shader` + `.arena` writers (validated) |
| `woplib/texlib.py` | texture generators (checker, tiles, bricks, planks, stone, metal, fabric, stripes, dots, frost, grime, neon, label) and `Textures`: one `TX.add` / `TX.material` call writes the image AND its shader |
| `woplib/padmath.py` | AimAtTarget maths: target placement, flight time, bspc limits |
| `woplib/wopdata.py` | WoP facts: classnames, forbidden items, bot weights, arena tokens, sounds that exist, common shaders |
| `templates/sample/` | the reference generator: hull, house + roof, pool + steps, secret vault, tower pad, cover, loot |
| `tests/run.sh` | regression tests: each rebuilds a bug a shipped map had and checks the checker catches it |
| `light_check.py` | floor brightness from the BSP lightmaps (reachable floor only, via the .aas): dark and blown-out areas, `lights.png` |
| `preview/autoviews.py`, `montage.py` | review cameras generated from the map (every weapon, secret, pad landing, overviews) and one labelled `review.png` |

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
5. Items, pads, secret, movers, lights, sounds. `K.fix_items()` last, then `TX.write_shader()` (brush + model shaders,
   levelshots, arena). **MUST** register every model shader before the `.shader` file is written (late registrations
   draw black/grey). Textures: one `TX.add(name, array, kind, steps=)` per brush texture and `TX.material(key, array,
   kind, lathe=)` per model texture (lathe=True for labels on revolved models); never keep a separate name list.
   Use the `texlib` generators with the map's own palette; write a local function only for theme-unique art.

**2b. MUST: review the quick preview with the user before any full build.** `wopbuild.py <folder> preview`
(= gen + quick, about 20 s) builds a -meta-only BSP (no vis, light, bspc or bots) and an unlit, normal-shaded 3D
walk-through `<out>/quick.html` with the mapinfo camera buttons; it still reports a leak. Publish it with the Artifact
tool (republish to the same URL each round; copy the FRESH `quick.html` into the publish path every round - a stale
copy republished the old layout once) and ask the user to look at layout, scale, props and clutter. Every round
of tweaks is edit generator -> `preview` -> republish, nothing more. Start step 3 only when the user says the layout is
right (or the run is unattended and the layout is settled): full builds (vis, final light, bspc, bot matches,
screenshots) take tens of minutes and cost the user's usage allocation. Fix overlaps the preview can't show by
running `lint` (no compiler, a minute or two) before showing a round. Night mood and dark corners only show in the
full build: say so when you share the preview. Don't fill an open space (a street, a yard) with props just to push
sightlines under 4 %: the user called that "too busy"; keep cover where it reads naturally and accept a looked-at WARN.

**3. Loop `wopbuild.py <folder> check`** (gen, lint, compile, aas, lights, sight) until every step is PASS. Use the
symptom table (section 2). A WARN is fine only after you looked at it. Every step prints what moved since the last
run (`sight long_ray_pct 2.8 (was 6.0)`), so you can tell a fix from a regression. lint `boxes` lists plain brush
boxes no model dresses - the "looks boring" complaint before the user makes it.

**4. `wopbuild.py <folder> bots`**: every weapon picked up, secret found, few environmental deaths. Fix by moving loot,
adding pads from busy routes, botclip strips (section 6).

**5. `wopbuild.py <folder> render levelshots`**, then Read `<out>/review.png` (every screenshot on one labelled sheet:
your mapinfo shots plus automatic views of every weapon, secret entry and room, pad landing and two overviews),
`<out>/models.png` (every custom MD3) and `<out>/lights.png`. Look for stairs and ceiling edges, caulk holes,
floating/sunk models, plain boxes that should be props, mirrored or upside-down labels, rooms too dark/bright. Add
mapinfo shots for landmarks the automatic views miss (inside every building, on every roof); open a single
`shots/<name>.png` only to look closer.

**6. Final**: `wopbuild.py <folder> compile --light final` then `aas bots render levelshots package` (the .aas must be
rebuilt after the final light). Publish `<out>/walkthrough.html` with the Artifact tool (republish to the same URL for
updates), send `dist/X.pk3` + `dist/X_source.zip`, commit the generator on a branch and open a PR, and save a short
`claude/wop_<map>_notes.md` project note with new lessons.

### Definition of done (`report.md` says DONE)
- review: the user has seen the quick preview (`quick.html`) of the current layout before the full build
- gen: generator runs with `-W error::RuntimeWarning`, no kit warnings left unexplained
- lint: `audit_map` RESULT OK, `lint_map` RESULT OK (warnings looked at), `pad_check` every pad lands (t < 2.9 s)
- compile: no leak, q3map2 read the map's shader (build folder in the VFS), no model load failures, portals low
- aas: every pickup reachable from spawns, no TRAP, no OUT OF BOUNDS, every route in `routes.txt` works both ways standing
- lights: <= 10 % of reachable floor dark (raw lightmap < 30), <= 35 % blown out (> 200); WARN = look at lights.png
- sight: <= 4 % of eye-level rays over 1800u at every floor level in `mapinfo.json`
- bots: every weapon picked up, secret items taken, environmental deaths < 15 %
- render: walk-through <= 16 MB, review.png and models.png looked at; levelshots made
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
| user: "looks boring" / "plain box" (lint `boxes`) | brush blocks for buildings/furniture | custom MD3 (`K.solid_piece` keeps the same collision) + props + lights; the most frequent play-test complaint |
| user: "too busy" | props piled into an open space to push sightlines down | clear it back to a few natural pieces; review with `preview` before building |
| user: "too dark" (lights WARN, red on lights.png) | shade side of a house, secret rooms, under roofs; sunny maps are bimodal | fill lights at the listed coordinates; `K.light_grid` over big rooms |
| lights: a high top (shelf, cage roof) dark while the floor is fine | the light grid hangs below that top | lights above every high walkable top |
| aas: pad lands 300u+ off / on an object | a tall prop under the flight path (K.jumppad only reserves pad + landing) | move the prop off the arc |
| bots: reward weapon 0 pickups in some runs | it sits behind a two-pad / two-lift chain | add a direct pad from the floor or a busy route |
| setup: wopbspc link error "undefined reference to crc32" | an interrupted build left an empty .o | re-run setup_cloud.sh (it drops broken objects) |
| washed-out white floors (lights bright %) | too many overlapping point lights, strong sun on pale textures | fewer/weaker lights (raw 128 = neutral), darker floor texture |
| user: "secret too obvious" | visible entrance | hide it (underwater tunnel, fireplace, coffin, flour bin, drain) |
| aas TRAP on a high shelf/tray whose only drop is > 1000u | bspc traces walk-offs only 1000u down | an exit over a lower drop (botclip gap) or a pad (padfridge freezer) |
| lathe label upside down / mirrored on the contact sheet | revolve() v runs up, image rows run down | flip the image vertically before ML.T (padfridge `reg(lathe=True)`) |
| lint headroom: crouch-only strip along a ramp | the ramp top passes under the edge of the slab beside it | keep the ramp 64u off the slab edge |
| sight FAIL only on upper levels of a vertical map | levels look across an open atrium | cover on shelf fronts + tall props in the atrium; then `level_target_pct` in mapinfo |
| sight stuck high, rays cross props in the picture | eye-level gaps UNDER raised things (car on stands, boat/trailer decks, tables) | fill the gap (boxes stored under, a low deck from z 30); read `long rays by origin` in sight_*.log for where the rays start |
| sight: one huge doorway | a 3000u door joins two open spaces | split it (a pier: padgarage double door), then props either side |
| aas pad_aas FAIL "MID-AIR" / far from landing | bspc's own flight (10 % faster, 0.1 s steps, <= 3 s) hit an edge or fell short | more apex / start further back; two-stage access (shed roof, then roof) when one floor pad can't reach in 3 s |
| aas OUT OF BOUNDS (bots/players reach the scenery) | a gap in the boundary clip: slot in front of a gate, clip that stops short | gates flush with the playable side, clip to the sky over walls + hedges, one clip line at the street ends |
| sight/lights count gardens nobody can reach | eye points behind the clip | wopbuild passes `--aas` once the .aas is fresh (sightlines, light_check) |
| BSP 15-20 MB on a big outdoor hull | light grid over the whole volume, fine lightmaps on scenery | worldspawn `gridsize 192 192 256`; `q3map_lightmapSampleSize` 32-48 on scenery shaders |
| a light changes nothing in light_check | light inside a weapclip prop (culled), or a hidden closed surface between light and floor (a lofted body's flat top lid over a car cabin) | lights above props; skip lid faces in `loft(skip=)`; q3map2 log "culled lights" |

## 3. The user's standing rules
- Fill the map with catalog objects (https://worldofpadman.net/en/tutorials/catalog-map-objects/); main pieces
  (centrepieces, buildings, furniture) MUST be custom MD3s, not brush boxes.
- Never place a solid or entity inside another solid or entity (audit_map overlaps + point entities).
- Low portal counts (detail everything but the hull). Models fully on surfaces (no float/overhang).
- Break long sightlines with models (< 4 % of eye rays > 1800u), without making open spaces look cluttered.
- Hard-to-reach spots get the best weapons; 3-6 ammo spots per weapon, some hidden, some in plain sight.
- Every water area has a way out (steps/ramp or teleporter). Full explorability: every door enterable, every building
  climbable, roofs with a clear line of fire (no parapets/clutter).
- Bots must reach everything important (bspc AAS). Include `.shader`, `.arena`, textures, and a phone walk-through.
- Show the quick preview before any full build; full builds cost the user's usage allocation.
- Deliverables: `maps/X.map/.bsp/.aas`, `scripts/X.shader` (every custom shader), `scripts/X.arena` (map, longname,
  supported types only), `textures/X/*`, `models/mapobjects/X/*.md3`, levelshots, `X.pk3` + a source zip, and the phone
  walk-through (`wopbuild package` + `render` make all of them).
- Answers are in terms of NetRadiant Custom 20260114, q3map2 `-game quake3 -fs_game wop`, no gamepack.

## 4. Scale

Player box 30 x 30 x 56 (crouch 40), eye +26 over origin (origin = floor + 24), step 18, barrier jump 33.

| Style | Units | Catalog modelscale | Maps |
|---|---|---|---|
| Padman scale (tiny hero, giant room) | ~8 u/cm | 1.0 | playroom, xmas, lounge, shroom, tank, bakery, gelato |
| Backyard toy | ~5 u/cm | 0.6-0.9 | padbbq |
| Garage / street | ~6 u/cm (1 m = 600u) | 1.0 | padgarage |
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
- Crawl spaces (64u) work (`K.crawl()` to tell lint it is intended); bots ignored a weapon in a 48u crouch-only tube.
  `func_plat` elevators work (`K.elevator`).
- Spiral stairs with ~15-degree treads in a small tower (r < 120) give bspc broken links: add a lift pad.
- Playable area smaller than the sky hull (streets): mapinfo `bounds` = playable rectangle, `hull` = sky box, the edge
  closed with `common/clip` (solid for bspc), gates flush with the playable side; aas_check prints OUT OF BOUNDS.
- Count route use with trigger_multiple -> target_score probes (`AddScore` lines) when a spot gets no visits.

## 7. Jump pads (`K.jumppad`, `woplib.padmath`)
- trigger_push + target_position; AimAtTarget aims from the trigger CENTRE and the target is the APEX. Players keep
  their horizontal speed after the apex, so the target sits at t_up/(t_up+t_down) of the way (kit does it).
- **MUST** keep flight < 2.9 s (bspc predicts ~3 s); >= 20u clearance over edges (pass `edges=`); apex <= ceiling - 40
  under ceilings (pass `ceiling=`). pad_check can pass pads bspc doesn't link: +60-70u apex fixes it.
- **MUST** read `pad_aas.log` (wopbuild `aas` runs `pad_aas.py`): bspc's own end point for every pad, grounded or not,
  distance to the intended landing. bspc gives the pad 10 % more horizontal speed, steps 0.1 s, stops at 3 s: floor
  pads can't reach ~1450u up in time (padgarage roof: a woodshed roof at 800 as the first stage).
- `K.jumppad` warns when the launch spot is already occupied (a prop placed first); a pad inside a prop has no area.
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
- Light: point lights fall off with distance squared. Measured (light_check median, 128 = neutral, 200+ washed out):
  `K.light_grid` 600u over the floor on a 512 grid: 900 -> 79, 1500 -> 124, 2200 -> 173; 300u over the floor on a 384
  grid: 300 -> 64, 600 -> 113, 900 -> 162. (The old "1800-2400 on a 450 grid" advice washed floors out.) Room lamps
  ~400 at floor + 150. Sun: `sun_int` 110 + `skylight` 60 kept the sample yard at median 108 with 3 % dark; sun 220
  with skylight 40 gave 215 (51 % blown out). Run the `lights` step; WARN = read lights.png. No `q3map_surfacelight` on shaders of dense MD3s (one emitter per
  triangle). Shaded sides of houses need fill lights.
- Glass: GL_ONE GL_ONE + dim const (`SH.glass`); waterfalls alpha-blended (`flow` kind), never pure additive.
  Neon on a dark backing board. Flames: autosprite2 on single thin quads (`cross_sprites` for merged MD3 surfaces).
- Light compile times: fast `-fast -samples 2 -filter` ~1-3 min; final `-bounce 2 -bouncegrid` 3-110 min (rises with
  lightmapped MD3s and open areas; over an hour on padgarage's street-sized hull, so it ships without bounce); run long
  compiles as background tasks.

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
- Big outdoor hulls: worldspawn `gridsize 192 192 256`, `q3map_lightmapSampleSize` 32-48 on scenery shaders, and never
  a single sealing brush under the floor slabs (48u crouch slots everywhere; lint headroom runs for minutes).

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
- `loft()` through closed sections leaves a flat lid at the section top (a car cabin went black): skip those faces.
- Animated bits: `deformVertexes move/wave` per surface (lava lamp blobs, fish tails, flies).

## 12. Catalog models
Place by real bounds (`K.model_on` / `K.catalog` use md3bounds.json; bush, cane4, muffin origins are off-centre).
No palm tree (custom). `tree_winter` is leafless (dead indoors). pad_fish/flame_angel face -x, origin at the belly.
waterplant1a/1b (318u) aquarium plants; padstatue_gold (243u) spinning centrepiece; telescope/cabin for dormers.

## 13. Sounds (wopdata.SOUNDS, all verified to exist)
Looped speakers near sources (`K.speaker`), `K.timer_sound` for occasional ones, `K.trigger_sound` for one-shots
(doorbell, applause on a summit). `pk3_check --game` proves every noise exists. Common ones (sound/world/...):
ambient/fire_crackling wind_icy wind_night water_rippling water_drippling water_flowing slime_bubbling floor_creaking;
machine/clock_ticking fog_horn fishtank transformer electric_sizzle fan_pc aircon freezer mechanics dingdong;
misc/wind_chimes secret_found alarm_buzzer bicycle_bell door_buzzer toilet_flush; human/applause footsteps_m snoring;
animal/bird_owl1 cricket_chirp1 dog_bark2 kitten_meow blackbird.

## 14. "Deluxe" features the user likes
Movers (rotating/swinging/orbiting decor), a hidden secret room, an alternative way up (tractor beam, bubble lift,
suction pipe = `K.tube_lift` (trigger_push in a glass tube MD3, vertical through a hole or along the flight)), wire cages
(`K.cage_box` / `K.cage_round`), slides (`K.slide`), ambient + timed + triggered sounds, neon,
animated externalmodels, cloud layer (`SH.sky(cloud=...)`), levelshots, the phone walk-through. "Make it twice as
awesome" went best as a second connected area (balcony, frost deck, wave hall) keeping the old layout. Real-world
reference photos (a driveway, a street) are welcome: match the look (materials, trim, lanterns) but keep it uncluttered.

## 15. Compile commands (what wopbuild runs)
```
q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/X.map      (quick preview stops here)
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
