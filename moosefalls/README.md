# Moose Mountain Falls (wop_moosefalls)

**Deluxe (Oct 29):** the map doubled - a snowy outdoor **Frost Deck** and a second timber hall, **Thunder Bay**, joined to
the lodge through three doorways in its south wall (`wing.py`, `wing_models.py`; see "Deluxe wing" below).

An FFA indoor water park in a big timber lodge on a snowy evening, inspired by the Moose Mountain Falls park at Timber
Ridge Lodge (user's reference photos): glulam rafters, painted columns, tan ducts and pendant floodlights under a
pine-board ceiling, a glass skylight along the ridge, a triangular window wall on the east gable and WoP's
`env/frost-bite512` snowy forest outside. Human scale (~32u per metre), hall 4096 x 3328, deck z 0, water z -16.
Almost everything is detail: a handful of portals, fast compile ~2 min, full bounce light ~10 min on 2 cores.

- `build_moose.py` - the map:
  - **Tree island** (centre): a giant pine (MD3: trunk, limbs, ~1500 crossed needle sprays) on an island ringed by the
    **Lazy Bear River** (48 deep, wadeable; 16u stair exits on both banks, two plank bridges with rope rails). A spiral
    stair round the trunk climbs to the **Eagle's Nest** deck (Pad shield, Imperius ammo); a pad fires you up to the
    **crow's nest** (Imperius). Bubble G at the foot of the tree, Speedy on the river floor.
  - **Activity pool** (north-west): lily-pad crossing under a cargo-net frame, basketball hoop, beach entry, ladders,
    a rock island in the deep end; **Splasher on the bottom of the deep end**.
  - **Grotto** (north-west corner): a sealed rock mass with a waterfall. SECRET: dive under the waterfall - an
    underwater tunnel (top 80u below the surface, invisible from the deck; only a faint glow hints at it) comes up in a
    pool inside the cave; underwater steps (16u rise) lead up out of it - a sheer pool wall needed a pixel-perfect
    water jump and players got stuck (Pad Power, Imperius/Splasher/Betty ammo, secret sound). Swim back out the same way.
  - **Timber Peak** (north-east): log-cabin slide tower; 16u stairs wind up the outside to the platform (Pumper), a pad
    to the shingle roof (Floater, Imperius ammo). **Yellow Jacket** (closed tube, MD3) circles the tree island and
    drops you into the river; **Green Gulch** (open flume, MD3) runs down the east wall into the plunge pool. Slide
    floors are slick player-clip (`moosefalls/slide_clip`), walls weapon clip.
  - **Plunge pool** (east): steps down into deep water (Killer Ducks on the bottom), ladder, lifeguard chair.
  - **Moose Lodge Grill** (north): walk in at the side door under the moose-head trophy (Boaster in the kitchen,
    health station out front). Kitchen MD3s: griddle with burgers under a stainless hood, fryer, soda fountain, glass-door
    drinks cooler, pizza warmer and register on the counter, wall shelves with catalog tins and cups, pendant lamps;
    menu board on the back wall. Porch: five bar stools, hanging lanterns, a chalkboard specials A-frame. A bell dings
    when you step up to the counter.
  - **Summit Deck** (on the grill's roof, stairs on the west side): a giant burger sculpture (cover), two striped
    umbrella tables, an HVAC unit, festoon string lights, railings, the SUMMIT DECK sign (Visionless, Boaster ammo);
    walk on down the porch roof.
  - **Tiny Timbers** (south-east): log play structure on a triangle-mosaic splash pad - crawl tunnel through the base,
    stairs to the deck, blue and teal kids' slides, cabin roofs, a pad up to the tipping-bucket tower (Betty), water
    jets.
  - **Lookout stump** (south-west): walk into the hollow trunk; a pad inside (and one outside) fires you onto the top
    deck (Balloony) with a little log hut (walk in: Revival; steps to its roof).
  - **Whirlpool spa** (south): raised rock-ringed tub (cover).
  - Carved wooden moose on a rock plinth, Adirondack chairs, loungers, table sets, lifeguard chairs, inner-tube racks,
    floating tubes, catalog winter pines in planters, ferns, bushes, beach balls and big rubber ducks break up the
    deck (sightlines 3.6% of rays over 1800u).
- `moose_models.py` - every custom MD3 (pine, slides, rafters, ridge beam, ducts, columns, lamps, log cribs, gable
  roofs, posts, railings/rope fences generated per run, moose, boulders, rock skins, stump, tubes, furniture, bucket,
  hoop, ladders, net frame), textures and model shaders.
- `moose_textures.py` - brush textures (original art: flagstone deck, pool tile, splash pad, pine ceiling, glulam, log
  walls, signs, mural...), `moosefalls.shader`, `wop_moosefalls.arena` (ffa lps team ft syc_ffa syc_tp).
- `layout.py` - shared constants (hall, pools, island, tower, slide paths) for the builder and the models.
- `routes.txt` - on-foot routes for `aas_check.py --route` (the grotto is swim-only, so it is checked as a pickup).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_moosefalls_source.zip` into a folder the game sees (for example `wop/zz_moosefalls.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_moosefalls.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_moosefalls.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_moosefalls.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_moosefalls.bsp

## Lessons
- `meshlib.save_md3` now splits big surfaces greedily by vertex count (<4000 verts, <8000 tris per surface); the
  old fixed 2600-triangle chunks overflowed the vertex limit on dense alpha foliage.
- Railings that share a corner post produce coincident boxes and q3map2 "Duplicate or Flipped triangle" warnings;
  `gen_railing`/`gen_ropefence` remember built post positions.
- `sightlines.py --hot N` lists the 128u cells most long rays cross: put blockers there (here: the river's east reach).
- Slides as MD3 + brushes: floor = slick nodraw player clip (`slide_clip`), walls/roof = weapclip, supports only where
  `on_deck()`; the model's water strip is an additive scrolling surface 1.5u above the clip floor.

## Deluxe wing (`wing.py`, `wing_models.py`)
South of the lodge (whose south wall now has three doorways at x -1408 / 128 / 1664):
- **Frost Deck** (y -2464..-1696, open to the frost-bite sky): Steam Lagoon (heated pool, 80 deep, 16u steps at both ends,
  a hot-spring rock with a snowy pine, steam sprites), an **ice rink** (slick, boards, lamp posts; Boaster + Speedy in the
  middle), a **fire pit** with Adirondack chairs (Bubble G), snowball forts, snowmen, snowy pines, an ice moose (the wooden
  moose MD3 with `_remap` to an ice shader), festoon lights, falling-snow sprites, snowbanks + player clip at the ends.
- **Igloo** (west): walk in through the tunnel. SECRET: the ice-fishing hole in its floor is a trigger_teleport into the
  sealed **Ice Cave** under the deck (Imperius, Pad shield, Imperius ammo, icicles, ice crystals, secret sound); a
  teleporter brings you back beside the igloo.
- **Thunder Bay** hall (y -5056..-2496, its own roof pitch, rafters, skylight, lamps):
  - **Wave pool** (west): deep end at the wave-machine wall (Betty on the bottom), sloping sand beach, sea stacks (MD3 rock
    piles on clip cores), visible travelling waves (`water_wave`: tessSize 64 + two deformVertexes waves), ocean sound,
    a fog-horn timer, floats and a big lifeguard chair.
  - **Wave-machine house**: walk in at the north end (spinning flywheels on func_rotating, pipes, machine noise); a pad
    from the deck lifts you onto the **Storm Deck** roof (Splasher) - the pool side is open, dive in.
  - **Avalanche Peak**: stone core (walk-in room under the north flight) with four 10-step 16u flights round it to z 640
    (Balloony, Imperius ammo) and an express pad from the east. Two slides:
    - **Black Hole**: closed violet tube with glowing rings, a 1.25-turn helix into its own splash pool;
    - a teal flume into the **Tornado Bowl**: a 900u slick cone (24 wedges, 27 deg) you spiral round and drop through the
      104u hole into the splash pool below (16u steps out).
  - **Cocoa Cabin** (log cabin, walk in; pad to its roof deck: Pumper).
- Weapons: every type now has two copies and 6 ammo spots; 30 spawns. Sightlines 4.0-4.1 % over 1800u.

### Lessons (deluxe)
- Decoration placed by "nearest free spot" will happily fill doorways: reserve walk paths (NOGO) through every door and
  entrance BEFORE placing props, or aas_check routes report NO AREA.
- Item/weapon/spawn helpers now add a KEEP_OUT disc, so props placed later never land on a pickup.
- Stair flights wrapped round a core block the ground floor if every step is a solid block from z 0: make the upper
  flights thin 16u treads (you walk under them) and keep only the first flight solid.
- A pad in front of a door launches people who just want to walk in: keep pads off door approaches.
- Rocks in water: brush cylinders with a rock texture look cheap; use a sculpted MD3 (`seastack`) on an invisible
  weapon-clip core (tapered so the model hides it), carve the water with the core.
- Model names must be unique per variant: `duct(hang)` saved two different ducts under one name and the main hall's ducts
  sank into the roof.
