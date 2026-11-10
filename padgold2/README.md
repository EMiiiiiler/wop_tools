# Gold Rush Gulch: Flood Day (wop_padgold2)

Reimagining of `padgold/`. Status: **full build DONE** (Nov 2026, see Checks below). Merged with `padlagoon` for
`K.current()` / `K.flume()` / `stair_wedge()` and the `sightlines.enforce` flag.

Preview: `wopbuild.py padgold2 preview`, then publish `out/quick.html` to
https://claude.ai/artifact/TUyaMiR8jxdoSAA7pi3yfa (same URL each round).

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

## Checks (full build, Nov 2026) - report.md DONE
| step | result |
|---|---|
| gen | PASS, 0 warnings (`-W error::RuntimeWarning`) |
| lint | WARN looked at: audit OK, lint OK, every pad lands; 4 crouch-only "floors" are the steamer cabin window sills (52u windows), 2 plain boxes are the rock abutments (canyon architecture) |
| compile | 10 portals, BSP 5.3 MB, final light (-bounce 2 -bouncegrid) 52 s |
| aas | 16 routes OK both ways, every pickup reachable, 14 pads all linked by bspc (pad_aas) |
| lights | median 115, dark 1.6 %, blown out 1.0 % |
| sight | 5.9 % of eye rays > 1800u (reported only: water-park rule) |
| bots | 3 min, 10 bots, 53 kills; every weapon taken (Boaster 43, Betty 27, Pumper 8, Bubble G 7, Splasher 7, Balloony 6, Imperius 3), secret items taken (Pad Power 2, Revival 5, Killer Ducks 10), 1 environmental death |
| render / package | walk-through 3.5 MB, 31 screenshots, 5 levelshots, pk3 3.8 MB, source zip 1.9 MB |

Built in the full build:
- Currents (`K.current`, which now takes `pitch` and a sloped trigger `brush`): river RIV1 three 160u zones in
  mid-channel (x +-96, >= 64u off both kerb steps) flowing south at 170 u/s; east leg two zones flowing east (ending
  200u short of the lake stairs). Spillway: three sloped zones lying on the ramp (not cut into it) push 520 u/s down
  the 35.8 deg slope - it plays as a slide and is no longer walkable upward. No bot drownings or falls.
- Dressing MD3s (`gold2_models.py`): penstock valves with riser pipes and hand wheels on the dam face (x +-630), a
  sluice-gate frame with winched-up leaf at the spillway head, capstan/bollards/rope on the steamer's aft deck.
- Fill lights on the shade (east) faces: mesa face, tramway, west boardwalk, behind the east row, under the tower and
  flume, lake bed, vault corners, dam face (dark 12.2 -> 1.6 %).
- `pad_cap_yard`: second pad from the yard west of the tower straight onto the cap (Betty 0 -> 22-32 pickups; the
  floor -> catwalk -> cap chain alone got none).
- Pumper moved from the pit floor to the chamber floor beside the pit (-1880, 160): four runs with it on the pit floor,
  a stair step or the pit rim gave 0 pickups and the bots did not even enter the mine (target_score probes), although
  bspc links the pit both ways (routes, reach list, cluster portals all valid). A pumper ammo now sits in the pit.
- Siding seed uses zlib.crc32 (stable between runs) in `padgold/gold_models.py`.

Lessons: botlib ignored every pickup *inside* the 128u mine pit (trench + 16u stairs) while the same weapon on the
chamber floor 200u away got 33 pickups - the AAS looked correct; if a pickup in a pit gets 0, try it on the rim
floor first. A two-pad chain (floor -> catwalk -> cap) is a cul-de-sac for bots; one direct floor pad fixed it.
