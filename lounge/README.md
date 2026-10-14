# Couch Lock (wop_padlounge)

A free-for-all map in a stoner's living room late at night, at Padman scale (~8u per cm, catalog models at 1.0).
x east, y north, floor z 0, ceiling z 2048, room 4096 x 3584. The whole room is one fog volume (a light smoky haze,
`fogparms ( 0.22 0.22 0.2 ) 11000`). Everything except the shell is detail: 2 portals, BSP+VIS+fast light ~35 s,
full bounce light a few minutes on 2 cores.

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
- bspc predicts jump pad flights for at most 3 seconds: a pad whose flight takes longer (the first tent-roof pad, 3.1 s)
  gets no reachability and bots never reach the landing. Keep pad flights under ~2.9 s (pad_check prints `t=`).
- A 64u crawl space under furniture (crouch only) works for bots: the AAS links it and bots took the Boaster.
- The preview now honours texture alpha for alpha-blended shaders (smoke, decals) instead of a flat 55% opacity.

## Bot tests (wopded, 10 bots, FFA 3 min)
- Final layout: 46 kills, every weapon taken: Imperius (bookshelf top) 35, Pumper 21, Boaster (under the couch) 14,
  Bubble G 13, Splasher (TV stand top) 10, Betty (tent roof) 4, Balloony (couch back) 2; Killer Ducks from the secret shelf 12.
- With the Splasher on the couch back, bots never fetched it in two runs; swapped with the Balloony it is taken 10-15x.
