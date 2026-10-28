# Couch Lock (wop_padlounge)

A free-for-all map in a stoner's flat late at night, at Padman scale (~8u per cm, catalog models at 1.0): the living room
(4096 x 3584, ceiling 2048, one smoky fog volume `fogparms ( 0.22 0.22 0.2 ) 11000`) and, through a sliding door, a
4096 x 3200 balcony over the night city. x east, y north, floor z 0. Everything except the shells is detail: 5 portals,
BSP+VIS+fast light ~3 min. Full bounce light (`-bounce 2 -bouncegrid`) took 112 min on 2 cores because of the
open balcony and ~90 lightmapped MD3s; `-fast -samples 3 -filter` without bounce is a good middle ground.

- `build_lounge.py` - the map:
  - **couch** (north wall): olive corduroy three-seater, seat 360, arms 560, back top 760 (Balloony). A pad on the rug jumps
    onto the seat (a falsa blanket is thrown over the east cushion); pads on the rug and on the side table reach the back.
    **Under the couch** is a 64u crawl space (crouch): Boaster, Imperius ammo, socks, storage boxes.
  - **secret**: the mouse hole in the skirting board at the back of the crawl space (secret sound + teleport) leads to the
    stash shelf above the couch: Pad Power, Killer Ducks, stash jar; a pad drops you back in front of the couch.
  - **coffee table** on the shag rug: the giant glass bong (MD3, weapon-clip frusta), ashtray with a smouldering joint,
    grinder, lighter, papers, pipe, Bubble G. A skateboard (MD3: kicktails, concave, grip tape, ply edge, trucks, wheels) leans on the south edge as a
    33-degree ramp, walkable through a clip slab under the deck; a pad on the east side too. A milk crate of records under the table breaks the long low sightlines.
  - **TV stand** (west): three walk-in compartments (health station, console, Pad shield), flat screen with a
    rotating psychedelic visualiser (surface light), floor speakers, a "chill out" neon sign. Pad to the top (Splasher).
  - **bookshelf** (east, 1600 tall): walk-in bottom shelf with records and the green lava lamp, a pad into the
    second shelf (Jumper, stash jar), a pad to the top (Imperius).
  - **grow tent** (south-west, 1280 tall): black canvas, door unzipped, mylar inside, three cannabis plants (MD3) under a
    purple LED panel, carbon filter and duct. Pumper inside, Betty on the roof (pad from outside the door).
  - **mini fridge** (north-east): door wide open, walk-in (Speedy, Boaster/Imperius ammo, munchies on the shelf), pad
    to the top. Floor lamp beside it.
  - **side table** (north-west): a pad up from the floor (purple lava lamp, Splasher ammo, pad on to the couch back),
    a stack of pizza boxes and two moving boxes by the TV as cover.
  - **floor**: hookah (MD3) between the TV and the tent, subwoofer, guitar amp, leather pouf + floor cushion, laundry
    basket, record crates, crisp bags (MD3), pizza stacks and an open pizza box, big potted plant (MD3), bean bag (MD3),
    RC car, rubber duck, crushed cans, trash bags.
  - ambience: fairy lights round the walls (pulsing coloured bulbs), lava lamp bubbling, TV, tent ventilation, fridge
    hum, crickets at the window and func_timer one-shots (a police car passing, a dog, the pizza delivery door buzzer,
    snoring from the couch, the bong bubbling).
- `balcony_build.py` - the balcony (v2, called from build_lounge.main()):
  - **outside**: the apartment block round the lounge (facade with neighbours' lit windows), a sky box with a painted night
    skyline (`env/padlounge/night_*`, moon on the south face), a street far below and two blocks of flats across it.
  - **deck**: sliding door (MD3 frame, glass panels parked outside) and a pet flap by the AC unit; glass balustrade with
    clip above it, bamboo privacy screens at both ends, wall lanterns, string lights on posts.
  - **spa platform** (east, 256 high, 16u stairs): a cedar hot tub (MD3) sunk into it, 268 deep water with steps out on
    the north side. Imperius at the bottom. **Secret**: the drain on the tub floor teleports you to the upstairs
    neighbour's balcony (Revival, Floater, ammo, a garden gnome, a sunflower, the neighbour's cat behind the curtains) with a
    teleporter pad back down. Loungers, telescope, Pumper on the platform.
  - **pergola** (west, rafters walkable at 1600): a `func_plat` lift up through a hatch (bots use it) and a jump pad from
    the house wall (players); Betty on top. Under it a rattan L sofa, table with a lantern and crisps, hanging baskets,
    a wind chime, festoon lights.
  - kettle BBQ (Splasher), AC unit with a spinning fan (func_rotating), patio heater (Bubble G), hammock on a stand,
    herb planter (Balloony), cooler, deck box, potted plants.
- `balcony_models.py` - the balcony MD3s and the layout constants they share with the collision: hot tub, pergola, sofa,
  table, BBQ, AC unit + fan, heater, loungers, planter, railings, sliding door, hammock, deck box, cooler, gnome.
- `balcony_textures.py` - deck boards, brick, facade + window glow, bamboo, street, far blocks, tub tiles, doormat, the
  neighbour's door and the six sky box faces.
- `lounge_models.py` - every custom MD3 (procedural meshes + textures + shaders): bong (glass, green water, rising
  bubbles, milky smoke, PADMAN decal, steel downstem, glowing bowl), lava lamps (wax blobs rise and sink with
  `deformVertexes move`), cannabis plants (alpha-cut fan leaves, frosty colas), hookah, ashtray + joint, grinder, stash
  jar, crisp bag + crisps, bean bag, lighter, skateboard (modelled leaning in place; `skate_top()` gives the clip line).
- `lounge_textures.py` - all textures (original art), `padlounge.shader`, `wop_padlounge.arena` (ffa lps team ft syc_ffa).
- `routes.txt` - on-foot routes for `aas_check.py --route` (tent door, skateboard, seat, back top, fridge, TV compartments, bottom shelf, table top).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh` (wopded smoke test + summary), `package.sh` (pk3 + source zip),
  `env.sh` (paths in a cloud session).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padlounge_source.zip` into a folder the game sees (for example `wop/zz_padlounge.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padlounge.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padlounge.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padlounge.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padlounge.bsp

## Lessons
- A jump pad onto a roof with an overhang (pergola rafters) failed in bspc twice: its predicted flight (0.1 s frames, stop
  at the first ground contact) ended under the rafters even though pad_check landed it. A `func_plat` lift through a hatch
  gave bots 17 elevator reachabilities at once; keep the pad for players.
- Balcony sightlines: the deck started at 6.4 % of rays over 1800u; a deck box in front of the door (370u out), a
  cooler, two potted plants beside the door and the hammock/heater in the walkway took it to 3.6 %.
- bspc predicts jump pad flights for at most 3 seconds: a pad whose flight takes longer (the first tent-roof pad, 3.1 s)
  gets no reachability and bots never reach the landing. Keep pad flights under ~2.9 s (pad_check prints `t=`).
- A 64u crawl space under furniture (crouch only) works for bots: the AAS links it and bots took the Boaster.
- The preview now honours texture alpha for alpha-blended shaders (smoke, decals) instead of a flat 55% opacity.

## Bot tests (wopded, 10 bots, FFA 3 min)
- Final layout: 46 kills, every weapon taken: Imperius (bookshelf top) 35, Pumper 21, Boaster (under the couch) 14,
  Bubble G 13, Splasher (TV stand top) 10, Betty (tent roof) 4, Balloony (couch back) 2; Killer Ducks from the secret shelf 12.
- With the Splasher on the couch back, bots never fetched it in two runs; swapped with the Balloony it is taken 10-15x.

### v2 with the balcony (10 bots, FFA 4 min)
- 37 kills; every weapon taken: Bubble G 31, Pumper 27, Imperius 26 (bookshelf + tub bottom), Splasher 21, Balloony 16,
  Boaster 14, Betty 6 (tent roof + pergola via the lift). The tub-drain secret works for bots: Revival taken twice.
