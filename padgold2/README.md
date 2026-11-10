# Gold Rush Gulch: Flood Day (wop_padgold2) - PROTOTYPE

Reimagining of `padgold/`. Status: **quick preview only** (gen + lint clean, -meta compile without a leak). No vis,
light, bspc, bot match or package yet - that is the full build, to be done once the user is happy with the layout.

Preview: `wopbuild.py padgold2 preview`, then publish `out/quick.html` to
https://claude.ai/artifact/ (same URL each round; see the PR / project note for the link).

## The idea
The dam at the head of the gulch has let go. **Main Street is the river**, and every ride is a piece of the mining
works rather than a prop placed in a plaza (the user's "reimagined" brief on padlagoon: rides built out of the theme).
Three levels joined into loops, so you ride down and take a lift back up:

| level | what is on it |
|---|---|
| 0 - flooded town | plunge pool, Main Street river (wade-deep, kerb step both banks) with three buildings each side, east leg to the steamer lake, gold-pan pool, geyser field, mine tunnel through the mesa |
| 384 - mine mesa | ore-cart carousel (ridable func_rotating) round the Balloony, headframe, top of the mine-cage lift |
| 576 - the crest ring | dam crest + gatehouse, both abutments, water-tower catwalk (plank bridge), top of the flume, top of the tramway |

Ways up: mine-cage elevator (func_plat) -> mesa -> tramway ramp -> west abutment; switchback 16u stairs on the east
abutment; geyser pads (to the mesa, to the crest); water-tower pad -> catwalk -> bridge; walking up the spillway or the
flume. Ways down: **spillway slide** (crest -> plunge pool, 35.8 deg), **log flume** (east abutment -> lake, 14.5 deg),
the lift, jumping.

Roof pads launch from the FAR bank and fly over the river (the near bank is too close to clear the awnings).

## Loot ladder
Imperius gatehouse roof (top of the map, pad from the crest) > Betty water-tower cap > Balloony cart carousel on the
mesa > Pumper mine pit > Splasher bottom of the plunge pool > Boaster saloon > Bubble G store. Pad shield on the
steamer wheelhouse, Floater on the bank roof, Speedy on the nugget in the gold pan, Jumper on the lake bottom, Boomies /
Climber at the far ends of the abutments. Secret: outhouse behind the saloon -> the Mother Lode -> back to the west yard.

## Code
- `build_padgold2.py`: layout constants at the top; `shell()` is one thick structural slab with holes refilled to each
  floor height (no basin walls). Reuses `../padgold/gold_models.py` (models, textures, sky) + `gold2_models.py`
  (lift frame, pan rim, tram bents).
- `woplib/huts.py` (new, promoted from padgold): `brushes()` / `texfn()` for enterable buildings via
  `K.solid_piece`, and `Row` = street coordinates for buildings facing a north-south street.

## Hand-over notes for the full build
1. Water-park rule (padlagoon notes): sightlines are NOT enforced (`mapinfo sightlines.enforce false`); do not add
   props for the 4 % target. `wopbuild` on the padlagoon branch knows the flag; merge/rebase onto it first - it also has
   `K.current()` / `K.flume()` / `stair_wedge()`.
2. Currents (not in the prototype, the preview can't show them): a downstream current in the river in short zones
   away from the kerb exits, and a push down the spillway so it plays as a slide (keep it walkable upward from the side,
   or accept that the stairs/geyser are the way up).
3. Not yet checked by bspc: the func_plat lift, the 13 pads (cross-river roof pads fly 830u; pad_check t <= 1.9 s),
   the spillway foot (starts at the pool edge: the route from the pool is a water jump - add a 16u step if bots fail),
   the tramway and flume ramps, the kerb steps. Write routes for anything aas_check reports as NO AREA.
4. Lights are rough (room lamps only). Expect fill lights under the dam face, in the mine, under the tower.
5. Plain pieces to dress: abutments and mesa are rock boxes (lint `boxes`), the steamer cabin, the reservoir step.
   Ideas: valve wheels + pipes on the dam face, a sluice gate at the spillway head, a water wheel on the smithy.
6. `gold_models.materials()` seeds building siding with `hash(name)` (changes per run); pass a stable seed.
7. Arena: FFA set as scaffolded. Levelshots/shots in mapinfo are prototype cameras.
