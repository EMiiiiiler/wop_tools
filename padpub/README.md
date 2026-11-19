# The Padman's Arms (wop_padpub)

Generator: `wopbuild.py padpub gen` (or `OUT=<dir> python3 build_padpub.py`). Full pipeline: `wopbuild.py padpub all`.
Models + textures: `pub_models.py` (all original procedural art).

## Design sheet
- Theme + scale: a Victorian London pub (reference photo: dark mahogany back-bar with arched red/gold etched mirrors,
  long curved counter with brass hand pumps, red/black/cream encaustic tiles in front of the bar, brass chandeliers,
  green tapestry banquettes, hunting prints, red ceiling). Toy scale ~5u/cm like padpizzeria: bar stool 375, table 380,
  counter 550, back-bar cornice 1360, ceiling 1600.
- Playable area: x -2560..1600, y -2100..1600 (4160 x 3700). x east, y north (street south, bar north).
- Centrepiece: the five-bay back-bar gantry (custom MD3 per bay: cabinet or lit fridges, marble back counter, optics on a
  brass rail, bottle shelves, arched etched mirror, carved pilasters, cornice you can stand on) + the curved counter.
- Zones (each enterable and climbable):
  1. Saloon bar (x -1600..1600, y -1200..1600): counter top (pad), back counter (pad from behind the bar), gantry
     cornice "top shelf" (pad from the counter top), two settle-booth islands, front banquettes, fireplace with an
     overmantel you can stand on (pad), grandfather clock (secret), fruit machine.
  2. The snug (x -2560..-1632, y -200..1600): upright piano (pad to its top), jukebox, dartboard + oche, tables, settle.
  3. Beer garden (x -2560..-1632, y -1232..-232, open sky): picnic tables, parasol, barrels, tree planter.
  4. Pavement (y -2100..-1232): red phone box (walk in, pad to the roof), pillar box, lamps, A-board, swinging pub sign.
  5. Secret barrel cellar (sealed, below the world).
- Routes: front door, side door (saloon <-> garden), snug door (saloon <-> snug), snug back door (snug <-> garden),
  garden gate (garden <-> pavement), round the west end of the counter to the staff floor. Loops everywhere.
- Loot ladder: Imperius on the gantry cornice (pad from counter top) | Betty on the back counter (pad from the staff
  floor) | Balloony on the overmantel (pad) | Pumper on the phone box roof (pad) | Splasher on the piano (pad) |
  Boaster on the counter top (pad) | Bubble G in the beer garden. 3-6 ammo spots each, some under tables / in the phone
  box / behind the bar.
- Water: none.
- Secret: walk into the open trunk of the grandfather clock (pendulum swinging) -> the barrel cellar (Pad Power, Revival,
  Killer Ducks, Pad shield) -> teleporter back behind the bar.
- Sightline blockers: settle islands (700u backs), banquettes, tables + stools, the counter, phone box, picnic tables.
- Sounds: fire_crackling (fireplace), clock_ticking (grandfather clock), floor_creaking, dingdong (front door),
  applause (top shelf), blackbird + bicycle_bell + police_pass outside, tv_upstairs (muffled).
- Jump pads: dressed as beer mats.

## Checks
(wopbuild writes report.md in the build folder)
