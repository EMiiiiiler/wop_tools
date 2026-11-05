# Mini Golf Madness (wop_padminigolf)

Generator: `wopbuild.py padminigolf gen` (or `OUT=<dir> python3 build_padminigolf.py`). Quick look:
`wopbuild.py padminigolf preview`. Full pipeline: `wopbuild.py padminigolf all`.

## Design sheet
- Theme + scale: a sunny putt-putt park at "toy" scale, ~4u per cm (Padman is a 14 cm toy, a lane is 90 cm wide).
  Catalog models at ~0.5 for small things, trees 2.5, sunflowers 1.6. Sky WoP env/fort-pad512 (sunny garden).
- Game types: FFA, LPS, team, FT, Sniper-and-Co.
- Playable area: 4608 x 4096 (x -2304..2304, y -2048..2048), turf at z 0, a hedge all round (scenery behind clip),
  trees beyond it.
- Six holes, each a felt lane with painted rails you hop over (24u: barrier jump), a tee mat, a cup and a flag:
  1 Windmill (through the windmill's base), 2 Volcano, 3 Lighthouse lake shore, 4 Clown (through the clown's mouth),
  5 Loop-the-loop, 6 Rolling hills (two humps).
- Landmarks (custom MD3, each enterable and climbable):
  - **Windmill** (centre north, 0,1000): walk through the tunnel in its base; a 16u stair from the east and a pad onto
    the stage (the deck round the mill, z 400) under the turning sails; a pad from the stage up to the lookout on the
    cap (Imperius).
  - **Lighthouse** (west, on an island in the lake): footbridge, walk into the keeper's room; a pad onto the gallery
    (Betty), walk into the lamp room from the gallery.
  - **Volcano** (east): stairs onto the lower terrace, pads up to the crater rim (Balloony); lava in the crater hurts.
  - **Clown** (south): walk in through the mouth and out the back; a pad onto the top hat (Pumper).
  - **Clubhouse** (south-west): walk in (Boaster, putter racks, ball bins, counter); stairs to the roof terrace.
  - Giant golf ball on a tee in the middle, the loop-the-loop over hole 5.
- Loot: Imperius windmill lookout; Betty lighthouse gallery; Balloony volcano rim; Pumper clown hat; Splasher on the lake
  bed by the island; Boaster in the clubhouse; Bubble G on the windmill stage. 3-6 ammo spots each.
- Water: the lake (36 deep, wading), ramps out south and east, steps round the island, the footbridge.
- Secret: the 19th hole behind the windmill - drop into the cup -> the Lost Ball Cavern (sealed, under the world:
  Pad Power, Revival, Killer Ducks, Pad shield) -> teleporter back.
- Sounds: birds, water, the windmill creaking, applause on the windmill lookout, the volcano bubbling.
