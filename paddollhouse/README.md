# Padman's Dollhouse (wop_paddollhouse)

An FFA map on a sunny afternoon in a girl's bedroom. In the middle stands **Rosewood Manor**, a huge pink Victorian
dollhouse, cut away at the back like every real dollhouse, so all its rooms open onto the bedroom floor. Padman is
doll-sized: the furniture in the house is about his size, the bed, the bookcase and the toys round it are giant.
~12u per cm. x east, y north, bedroom floor z 0, room 4608 x 4096 x 2560. The sun (from the north: the user plays in
New Zealand) shines in through the big window behind the house; WoP's sunny garden sky (env/fort-pad512) shows outside.

Everything but the room hull and the sky box behind the window is detail: 2 portals, fast compile ~70 s,
`-bounce 1 -bouncegrid` ~8 min on 2 cores.

- `build_dollhouse.py` - the map:
  - **Rosewood Manor** (2048 x 896, three floors of 336, three rooms each). Ground floor: the kitchen (range,
    dresser, larder, table, health station), the hall (front door to the porch, grandfather clock, the stair), the
    parlour (fireplace with a real fire, sofa, piano, Pad shield). First floor: the bathroom (a roll-top bath full
    of water with bath steps in and out: **Pumper on the bottom**), the landing (door out onto the balcony over the
    porch: Floater) and the master bedroom (four-poster). Second floor: the nursery (crib, rocking horse, a turning
    mobile, the tiny dollhouse - SECRET), the upper landing and the library (Visionless). Interior doors near the
    open back connect every floor; 16u stairs (21 steps of 32) wind up the hall: west, east, then west again out
    onto the **roof terrace**.
  - **Roof**: two walkable 40-degree gables with a flat ridge walk on top, the terrace between them, and along the
    cut-back edge into the two **attics** (Balloony in the west one, Boomies in the east one). The **tower** on the
    terrace: walk in through its door, a pad throws you up through the hatch onto its deck (**Imperius**), a fling pad
    takes you back down to the play floor. The parapet is 24u high, so nothing blocks fire from the roofs.
  - Pads from the bedroom floor up into the first-floor bedroom and the second-floor nursery.
  - **Front garden** on the house board under the window: lily pond (swim, 16u stone steps out, a sailboat circling
    on a func_rotating, Splasher ammo on the bottom), a swing (func_pendulum seat), picket fences, gnomes, flowers, a
    bonsai tree, mailbox, bench. Pads onto the balcony and onto the window sill (Boaster ammo).
  - **The bed** (east wall): pad onto the mattress (**Betty** by the pillows, a plush bunny); under the bed it is
    dusty and dark: shoeboxes, a suitcase, socks, dust bunnies, glowing eyes, **Bubble G**, BamBam.
  - **The bookcase** (west wall): three pads up to its shelves, the **Splasher** on the top shelf.
  - **The play floor**: braided rug, a teddy bears' tea party, letter-block towers, a spinning top (func_rotating), a
    beach ball, a pram, two toy trucks, stacking rings, drums, book piles, an RC car and a beanbag for cover.
    The toy chest against the south wall: crawl in through the broken plank (**Boaster**).
  - **SECRET**: walk into the open door of the tiny dollhouse in the nursery (secret sound) -> **the Doll's
    Ballroom**, sealed under the world: mirrors, a big chandelier, a giant music box with a turning ballerina; Pad
    Power, Revival, Killer Ducks, Imperius ammo; a WoP teleporter takes you back to the garden.
- `dh_house.py` - the house: `Wall` specs (slab + openings) shared by the collision brushes and the MD3 facade
  (pink clapboard, white casings with pediments, mint shutters, belt courses, cornice brackets, window boxes), the
  gable roofs (fish-scale shingles, gingerbread bargeboards, finials), the front gables with round windows, the
  tower (crenellated parapet, flag), the porch and balcony balustrade.
- `dh_models.py` - every other custom MD3/IQM: bookcase, book rows, bed, plush bunny, toy chest, tea set furniture,
  teddies, letter blocks, spinning top, beach ball, pram, rug, curtains, window frame, garden pieces, under-bed junk,
  ~40 pieces of doll furniture (1u = 1 cm, placed at 1.5x), toys, the ballroom music box and ballerina.
- `dh_textures.py` - brush textures (wallpapers per room, floors, flock, stone, jump pads...), `paddollhouse.shader`,
  `wop_paddollhouse.arena`.
- `layout.py` - shared constants (rooms, floors, stairs and their holes, roof profile); `dhlib.py` - shader registry.
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_paddollhouse_source.zip` into a folder the game sees (for example `wop/zz_paddollhouse.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_paddollhouse.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_paddollhouse.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_paddollhouse.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_paddollhouse.bsp

## Lessons
- A dollhouse at true 1:12 (1u = 1 cm) in rooms Padman can fight in (680 x 880 x 320) looks empty: the furniture is
  placed at 1.5x and every room got 6-10 pieces plus pictures, shelves and rugs.
- A flat ridge walk flush with the top edge of two 40-degree roof slopes gave bspc no walk link from the slope onto
  it (route "blocked" both ways); raising the ridge walk 4u above the slopes' edge fixed it.
- The gable wall under a sloped roof slab of vertical thickness T is the polygon between the eave points moved in by
  T / tan(pitch) and the ridge underside: including the outer eave corners makes a hull that cuts into the roof slab.
- `audit_map`'s support test needs vertices on the brush below: a roof drawn as one big quad per slope (4 vertices)
  "floats"; build the shingles as a grid.
- Mesh transforms must be rotations: building a profile in (x, z) and swapping axes with a reflection matrix flips
  the triangle winding relative to the normals and the faces vanish in game (`dh_models.RX90`).
