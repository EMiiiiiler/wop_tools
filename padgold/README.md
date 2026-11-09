# Gold Rush Gulch (wop_padgold)

Generator: `wopbuild.py padgold gen` (or `OUT=<dir> python3 build_padgold.py`). Full pipeline: `wopbuild.py padgold all`.
Models/textures: `gold_models.py`. Layout constants live at the top of `build_padgold.py`.

## Design sheet
- Theme + scale: Wild West mining town water park in a red-rock canyon, sunny (`env/fort-pad512`). Human scale ~32u/m
  (player 56u = 1.75 m; doors 112u, storeys 128-160u). Catalog western set (cactus, tombstones, film camera) at ~0.8-1.0.
- Playable area: 4608 x 4096 (x -2304..2304, y -2048..2048), stepped canyon strata outside, common/clip at the edge,
  sky hull 5632 x 5120 x z -?..2560. x east, y north, ground z 0.
- Centrepiece (custom MD3): the **water tower** at (-200, 1150): trestle legs, catwalk ring z 576, stave tank, shingle
  cone roof with a flat cap at z 1008 (Imperius). Switchback stair tower (16u steps) east of it + a pad from the west;
  pad from the catwalk to the cap. The **log flume** leaves the catwalk north, runs east through a rock "mine shaft"
  outcrop and drops south into the plunge pool.
- Landmark zones (each enterable AND climbable):
  1. Main Street (south): Livery stable, Saloon (mezzanine + balcony, Boaster at the bar), Bank (vault: armour),
     General Store (Bubble G; 16u alley stair to its roof + plank bridge to the Sheriff's roof), Sheriff's office + jail
     (Speedy in a cell), Blacksmith, Assay office. Boardwalk + awnings; pads from the street onto every roof.
  2. Water tower + flume (north centre).
  3. Mine mesa (west): walk-in mine tunnel from the south face -> chamber -> stepped gallery pit (Pumper) -> north exit.
     16u stairs up the east face to the mesa top; ore carts ride a circular track (func_rotating, ridable) round the
     Balloony; mine headframe.
  4. Geyser field (north-west): sinter cones; geyser pads onto the mesa and up to the water-tower catwalk.
  5. Paddle steamer lake (east): sternwheeler standing on the lake floor, pier from the west shore, cabin (walk
     through), bow stairs to the upper deck, wheelhouse (pad onto its roof: Betty), turning stern wheel. Splasher on the
     lake bottom; 16u steps out on the west shore.
  6. Plunge pool (north-east) under the flume; steps out on its south side.
  7. Gold-panning creek (centre, shallow) with the gold dredge (walk-in cabin, pad to its roof: Pad shield).
- Loot ladder: Imperius tower cap > Betty wheelhouse roof / Balloony mesa top > Pumper mine pit > Splasher lake
  bottom > Boaster saloon > Bubble G store. 3-6 ammo spots each.
- Water exits: lake (west-shore stair), plunge pool (south stair), creek 12u deep (walk out anywhere).
- Secret: the outhouse in the alley west of the saloon -> the Mother Lode (sealed gold cave under the town:
  Pad Power, Revival, Killer Ducks, Pad shield), teleporter back to the plaza.
- Sightline blockers: covered wagons, hay bales, barrels, crate stacks, water troughs, cacti, windmill pump, the dredge,
  the rock outcrop; boot hill (tombstones) NE of the steamer.
- Sounds: water_flowing (flume, plunge pool), water_rippling (lake), fire_crackling (forge), mechanics (ore carts),
  train_intercity on a timer, toilet_flush (outhouse), applause on the tower cap, cicada_chirp, secret_found.

## Checks
(wopbuild writes report.md in the build folder; paste the summary here when the map ships)
