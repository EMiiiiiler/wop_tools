# Sweet Padman's Bakery (wop_padbakery)

An FFA map inside a busy bakery kitchen and its little shop, at Padman scale (~8u per cm, catalog models at 1.0: a
muffin is as tall as Padman). x east, y north, kitchen floor z 0, ceiling z 2048, room 4608 x 4096.

Everything but the room shell, the street annex behind the shop windows and the sealed secret room is detail: 4 portals,
BSP + VIS ~10 s, fast light ~1 min, full light (-fast -samples 3 -filter -bounce 2 -bouncegrid) see Checks.

- `build_bakery.py` - the map:
  - **The show cake** (centre): a three-tier celebration cake (white with a chocolate drip, pink with dots and pearls,
    lilac with sugar roses) topped by a HAPPY FRAG DAY plaque and strawberries. Sugar-cube stair up to tier 1, pads up
    the tiers and a direct pad from the floor onto the top (**Imperius**, applause). A slice is missing on the east
    side: walk into the cake between the sponge and jam layers (**Boaster**); the cut slice stands beside it as cover.
  - **Deck oven** (west wall): walk into the warm proofer underneath (**Bubble G**), pads into both baking decks
    (bread on the hearths, Pad shield, Jumper) and onto the oven top (**Balloony**) beside the flue.
  - **Floor mixer** (north-west): a 60-litre planetary mixer, its paddle turning (func_rotating); a pad drops you into
    the bowl (**Pumper** on the bottom), a pad throws you back out.
  - **Counters** (north + east, worktop z 720): pads up from the floor, open shelving underneath with tunnels through
    the dividers at floor and mid-shelf level (Visionless), the wall shelf over the north counter with the canisters
    (**Betty**, pads from the worktop), the decorating station on the east counter with a cake turning on its
    turntable, a cupcake tower, piping bags, cookie trays, dough, a scale.
  - **Cool room** (south-east): walk in through the strip curtain (butter, eggs, milk, cakes waiting; Pad shield),
    pads onto its roof from the floor and from the east worktop (**Splasher**).
  - **Shop** (south): the display cabinet (step stools up into its lower deck from the kitchen, pads onto the glass
    shelf and the top: cakes, cupcakes, eclairs, the register, a cake under a dome; Speedy), cafe tables, a Padman
    standee, sunny windows onto a painted street, the OPEN neon, the chalk menu.
  - **Cooling racks** (south-west): two speed racks full of croissants, cupcakes, loaves and donuts; pads onto their
    tops (Climber, Boomies).
  - **SECRET**: climb the step stool of the flour bin (north-west) and jump into the flour -> **the Sugar Vault**
    under the world: chocolate walls, a chocolate fountain, a golden cake, rock candy, chocolate coins; Pad Power,
    Revival, Killer Ducks, ammo; a teleporter back next to the bin.
  - Cover: sack piles, ingredient bins, egg trays, milk crates, cake boxes, cupcakes, donuts, catalog gummy bears,
    muffins, fruit; pendant lamps, a ceiling fan turning over the cake, posters, a wall clock.
- `bk_shapes.py` - convex solids shared by the builder (invisible `common/weapclip`) and the models (visible
  surfaces via `bk_mesh.solids_parts`): oven, counters, cake + stair, mixer, display cabinet, cool room, racks, bin.
- `bk_models.py` - architecture MD3s (oven, flue, counters, cake, slice, mixer + paddle, display cabinet, cool room,
  rack, flour bin, wall decorations).
- `bk_props.py` - props (cupcakes, donuts, macarons, eclairs, croissants, breads, display cakes, sacks, crates,
  bowls, tools, jars, canisters, shop furniture, lamps, fan, vault treasures) with their collision (`BOX`/`CYL`).
- `bk_mesh.py` - mesh helpers + all model textures; `bklib.py` - MD3 shader registry and image helpers.
- `bk_textures.py` - brush textures (checker floor, subway tile, frieze, tin ceiling, parquet, diamond plate,
  street backdrop, signs, menu), `padbakery.shader`, `wop_padbakery.arena` (ffa lps team ft syc_ffa syc_tp).
- `layout.py` - shared constants. `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths; the toolchain is
  built by `../setup_cloud.sh`).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padbakery_source.zip` into a folder the game sees (for example `wop/zz_padbakery.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padbakery.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padbakery.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padbakery.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padbakery.bsp

## Checks (Oct 2026)
audit_map OK, check_entities OK, pad_check OK (24 pads, all under 2.5 s), aas_check OK (every pickup reachable, 12
routes: proofer, both counter tunnels at floor and mid-shelf level, the east tunnel, cake stair, cake cave, both
display step stools, both ways round the shop, the cool room door, the bin stair), sightlines 3.1 % of eye-level rays
over 1800u, 4 portals. Bots (10, FFA 3 min): every weapon taken (Imperius 17, Boaster 15, Bubble G 14, Splasher 6,
Pumper 6, Balloony 5, Betty 2), the secret found (Pad Power, Killer Ducks).

## Lessons
- Prop placement by occupied volumes (`FOOT` + `free()`): reserve every architecture brush's bounds first
  (`reserve()`), never a whole cabinet volume, or nothing fits inside the cubbies/cool room/display cabinet.
- A pad into an oven mouth behind a door ledge: the arc must peak right at the mouth (apex <= mouth top - 32) and stay
  above the ledge + 24 for the last ~120u; aim the landing just inside the mouth (`p_deck1`).
- Pads that pad_check passes may still get no bspc reachability (oven top, cake top, display top, rack top): +60..70
  apex fixed all four.
- Bots never took the Imperius at the end of a three-pad chain up the cake (0 in 3 min); one direct pad from the
  floor gave 17 pickups.
- Open under-counter shelving leaks long low sightlines through the divider doorways: a crate in every bay on the
  doorway line (walk round it through the front strip) took sightlines from 4.8 % to 3.5 %.
- An alpha texture whose alpha is >= 128 everywhere is fully opaque under `alphaFunc GE128` (the strip curtain); use
  the additive `glass` kind for see-through plastic.
