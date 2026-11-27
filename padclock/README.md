# PadClock Tower (wop_padclock)

Generator: `wopbuild.py padclock gen` (or `OUT=<dir> python3 build_padclock.py`). Quick look: `wopbuild.py padclock preview`.
Full pipeline (after the layout is approved): `wopbuild.py padclock check`, then `bots render levelshots package`.
Files: `build_padclock.py` (layout), `pc_models.py` (textures + every custom MD3/IQM).

## Design sheet
- Theme + scale: the inside of a giant clock tower at night, at Padman scale (catalog models at 1.0-2.0). Brick walls,
  oak floors and beams, brass and iron clockwork, the glowing dial seen from behind in the south wall.
- Playable area: one tower 4096 x 3072 x 2816 (x -2048..2048, y -1536..1536, z 0..2816; north = +y). One structural
  hull (floor, walls, ceiling, sealed night sky behind the dial window); everything else is detail / MD3 + weapclip.
- Centrepiece: an open atrium (x +-576, y +-704) runs the full height. At the top hangs the movement (brass plates,
  pillars, arbors) with a brass deck on it; a 1400u pendulum swings under it (func_pendulum + IQM), an escape wheel and
  rocking anchor turn on its east face, a train wheel on its west face. The bronze bell hangs above the deck from the
  ceiling beam; its flat crown (2560) is the top of the map.
- Levels:
  - Ground floor 0: chequered stone floor round the pendulum pit.
  - Gear Gallery 640: a ring round the atrium.
  - Escapement wings 1280: west, east and north of the atrium (the south band stays open from 640 up to the dial).
  - Dial balcony 1920 (south, in front of the dial) and Cuckoo ledge 1920 (north).
  - Movement deck 2080 (centre), reached by bridges with 16u stairs from both balconies.
  - Bell crown 2560, reached by a pad from the deck.
- Zones (each enterable AND climbable):
  1. Pendulum pit (ground centre): two pads up to the Gallery, Bubble G ammo under the bob.
  2. Mainspring barrel (ground SW): walk-in brass drum (door east), coiled spring inside (16u step), toothed lid by pad
     (Pad shield on top).
  3. Spare-gear stack (ground NE): four flat gears stacked in 32u steps (Boaster ammo on top).
  4. Gear Gallery (640): meshing wall gears on the north and south walls, crates, oil can, small gear stack.
  5. Chime house (1280 west wing): walk-in (door south), 16u stairs up its east side and a pad onto the roof (Splasher),
     wind chimes on a timer.
  6. Dial balcony (1920 south): the glowing dial with turning hands (Balloony in front of it).
  7. Cuckoo ledge (1920 north): the cuckoo house; the bird pops out of the window on a timer (func_door + model2,
     nonsolid) with a ding-dong. Pumper at the east end.
  8. Movement deck + bell (2080 / 2560): Betty on the deck, Imperius on the bell crown.
- Rooms: every level is split into rooms by brick partition walls with oak doorways (32 thick, doors 192 x 192,
  staggered so no ray runs through two in a row). Ground: an arcaded enclosure round the pendulum pit (two doors a
  side) and radial walls along the atrium edge lines (eight rooms). Gallery and wings: the same cuts, a cross wall
  through each wing. Balcony and ledge: two cross walls each. 64u oak balustrades with brass caps run round the atrium
  on the Gallery and the wings, along the wings' open south edge and along the balcony/ledge fronts, with gaps where
  pads cross and where you drop down. (Round 1 had none: sightlines were 22-29 %, now 2.7 / 3.5 / 3.7 / 5.1 %.)
- Routes: ground -> Gallery by the east-wall flight (16u), the west weight lift (func_plat) or two atrium pads. Gallery ->
  wings by the west-wall flight or the east weight lift. Wings -> Cuckoo ledge by the flight along the ledge or the
  east-wing pad (added after bots never took the Pumper). Wings -> Dial balcony by two pads. Balconies -> deck by the
  bridges; north wing -> deck by a pad; deck -> bell crown by a pad. Down: walk off anywhere (no deadly drops).
  The two Gallery -> Dial balcony pads of round 1 went: the south-band partitions left no launch spot bspc could fly
  over the balcony edge from.
- Loot ladder: Imperius bell crown; Betty movement deck; Balloony dial balcony; Pumper cuckoo ledge; Splasher chime-house
  roof; Boaster Gallery; Bubble G inside the barrel. 3-4 ammo spots per weapon (open floor and tucked away: behind the
  barrel, inside the chime house, under the cuckoo ledge, on the deck). Speedy Gallery, Floater east wing, Jumper ground,
  2 shards, Pad shield on the barrel lid. Health stations ground NW and east wing. 17 spawns over every level.
- Water: none.
- Secret: walk into the dark doorway of the cuckoo house -> the Cuckoo's Nest, a sealed room under the tower (Pad Power,
  Revival, Killer Ducks, Pad shield) -> teleporter back onto the Cuckoo ledge; secret_found trigger in front of the door.
- Dressing (round 2, "heaps of MD3s"): 37 flickering oil lanterns on chains (each with a light), 14 wall clocks with
  turning hands, 9 pairs of small turning wall gears, the leading-off rod from the movement to the dial, 4 watchmaker's
  benches with lamps/watches/keys/chess pieces, 6 hourglasses, oil barrels, toolboxes, giant springs, big pocket
  watches, old clock faces, paint tins, winding keys, nuts, a telescope, a gold Padman statue, a giant duck, animated
  ravens, spiders, cobwebs, hanging weights, tubular chimes, and a nest with eggs in the secret room. ~200 models.
- Sightlines: partitions + balustrades; the atrium-facing top level (zmax 1984) has level_target_pct 6 (5.1 %).
- Sounds: clock ticking at the movement and in the vault, mechanics at the wall gears, ding-dong with the cuckoo,
  wind chimes on the chime house, night wind at the dial, secret_found.
- Arena: ffa lps team ft (not symmetric, so no CTL).
