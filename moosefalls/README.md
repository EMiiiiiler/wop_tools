# Moose Mountain Falls (wop_moosefalls)

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
