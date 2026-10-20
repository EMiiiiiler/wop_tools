# Pumpkin Hollow (wop_padhalloween)

An FFA Halloween map: a hollow ringed by steep earth banks and dead woods on a moonlit night. A huge orange harvest
moon (a witch on her broom crossing it) hangs behind Blackwood Manor; jack-o'-lanterns, lamps and lit windows give the
warm light, the moon a cold blue one. ~64u per metre, Padman normal-sized, the pumpkins fantasy-giant.
x east, y north, ground z 0, playable ground 4608 x 4096 inside a sky hull 6656 x 6144.

Everything except the sky hull and the sealed lair is detail: 0 portals ("No portals means no vis" is expected).

- `build_halloween.py` - the map:
  - **Blackwood Manor** (north): a Second Empire house with a mansard roof. Walk up onto the porch and in through
    the front door: the hall (portraits, clock), the parlour (fireplace, armchairs, a grand piano, health station),
    the dining room (long table, candelabra, chandelier) with the staircase up along its east wall. Upstairs: the
    bedroom (Visionless), the landing with the door out onto the balcony on the porch roof, the library (Pad shield).
    Two pads on the balcony throw you onto the roof deck (widow's walk, iron cresting low enough to shoot over),
    four steps lead into the **cupola** (Imperius). A fling pad takes you back down. Bats circle the cupola and a bat
    weathervane turns on the onion dome. Back door to the garden.
  - **Graveyard** (north-west): wrought-iron fence with three gates between stone pillars topped with
    jack-o'-lanterns, rows of headstones (six custom kinds with epitaphs) with grave mounds and zombie hands, dead
    trees, two ghosts drifting between the graves, ground mist (a fog volume). **The mausoleum**: walk in, sarcophagi
    on the side ledges, the stair goes down the middle into **the crypt** (Pumper) under the graveyard - vaulted
    ribs, sarcophagi, coffins, skulls, candles. A pad beside the mausoleum gets you onto its roof.
  - **SECRET**: step into the open, glowing coffin standing at the west end of the crypt -> **the witch's lair**
    (sealed under the world): a rune circle, a turning crystal ball, potion shelves, bats; Pad Power on the dais,
    Revival, Killer Ducks; a WoP teleporter takes you back to the gate.
  - **The Great Pumpkin** (north-east): a house-sized carved jack-o'-lantern. Walk in through its grin; inside a
    giant candle and a pad that shoots you up through the lid hole onto its top (Balloony), a fling pad back down.
    The cut-off lid lies beside it. Around it the pumpkin patch: pumpkins of every size (cover), jack-o'-lanterns,
    hay-bale stacks, a scarecrow with a crow.
  - **The hanging tree** (centre): a giant dead oak. A spiral plank stair winds round the trunk up to the
    treehouse deck (Betty) and its hut; a pad to the hut roof. Lanterns hang in the branches, a tyre swing sways.
  - **The witch's cottage** (south-west): half-timbered and crooked; walk in (Bubble G, bed, black cat, potion
    shelf, spellbook, a little cauldron) - she cackles when you come in. A pad gets you onto the ridge (Speedy).
  - **The cauldron**: a giant iron pot bubbling on its fire. A pad drops you into the green brew, the Splasher lies on
    the bottom, steps up the inside lead back out to the rim.
  - **Corn maze** (south-east): 7 x 7 cells of corn; Boaster on the stage in the middle under a scarecrow; BamBam,
    a Floater and ammo in the dead ends.
  - **Gate plaza** (south): the stone gate with its iron arch and the PUMPKIN HOLLOW sign, low stone walls, a hearse,
    health stations. West: the bonfire with log benches. East: the pumpkin stand and the hay wagon. The old well by
    the manor path.
- `hw_models.py` - every custom MD3/IQM (procedural meshes, textures): the Great Pumpkin (smooth carved openings:
  quadtree-refined cells + jambs along the face polygons, `carved_shell()`), jack-o'-lanterns, pumpkins, leaves,
  dead trees, the treehouse, headstones, fence, gate pillars and arch, coffins, sarcophagi, candles, zombie hands,
  hay, scarecrow, lamps, cauldrons, broom, hat, cat, potion shelf, furniture, hearse, well, stand, wagon, bonfire,
  corn walls; movers (IQM): bats, ghosts, crystal ball, weathervane, tyre swing.
- `hw_houses.py` - the buildings: a `Wall` spec (slab + openings) shared by the collision brushes and the MD3 facade
  (siding/stone/plaster quads, frames, shutters, sills, corner boards, bands), the manor (shell, mansard roof with
  dormers, porch, cupola, chimney caps), the mausoleum, the crypt vault ribs, the cottage, the treehouse hut.
- `hw_textures.py` - brush textures, the night sky cube `env/padhalloween/night_*` (harvest moon with the witch,
  clouds, hills with dead trees and a church spire), `padhalloween.shader`, `wop_padhalloween.arena`.
- `layout.py` - shared constants; `hwlib.py` - shader registry, image helpers.
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padhalloween_source.zip` into a folder the game sees (for example `wop/zz_padhalloween.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padhalloween.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padhalloween.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padhalloween.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padhalloween.bsp

## Lessons
- Polygon cut-outs in a lathe surface: classify each cell against the polygons, subdivide only the cells a polygon
  edge crosses (quadtree, bilinear inside the cell), and build the jambs along the true polygon edges. Outlines come
  out smooth at a fraction of the triangles a uniformly fine grid needs (`hw_models.carved_shell`).
- Shaders of models made by the builder (the graveyard fence) must be registered before the shader file is written:
  `TX.make_all(OUT, extra_models)`.
- Decals (dirt paths, the hall runner, a pad on a sloping roof) need their own nonsolid shader variant (`dirt_ns`,
  `carpet_ns`, `jumppad_ns`), or they are 1u solids that also fail the audit (spawn/teleport boxes "in solid").
- bspc strips fog contents, so a ground-mist fog volume does not turn into bot "water".
- `fix_items()` nudges any pickup or spawn that ended up inside collision to the nearest free spot on the same floor.
