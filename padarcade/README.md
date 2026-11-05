# Midnight Arcade (wop_padarcade)

Generator: `wopbuild.py padarcade gen` (or `OUT=<dir> python3 build_padarcade.py`). Quick look:
`wopbuild.py padarcade preview`. Full pipeline: `wopbuild.py padarcade all`.

## Design sheet
- Theme + scale: an amusement arcade after closing time, Padman scale (~8u per cm, catalog models at 1.0): the
  cabinets tower over Padman, neon everywhere, a cosmic arcade carpet. FFA / LPS / team / FT / SYC.
- Hall 4608 x 4096 x 2048 (x -2304..2304, y -2048..2048), one structural box (walls, carpet floor, ceiling).
- Landmarks (custom MD3 on weapclip collision; every machine can be entered or climbed):
  - **Claw King** (centre): the giant claw machine. Walk in through the prize flap on its east side, up the prize
    chute ramp inside the base and out through the prize hole into the glass case: the Imperius sits on top of the
    plush pile under the swinging claw. A pad onto the roof (Splasher).
  - **Roll-a-Ball alley** (east): three skee-ball lanes; walk up a lane to the target deck, the 100-ring is a jump pad
    onto the top of the backboards (Balloony).
  - **Air hockey** (west): a glowing table you can stand on (Pumper), 16u stairs up its north side and a pad; puck and
    mallets as cover.
  - **Prize wall** (south-west): 16u stairs onto the first shelf, a pad to the top shelf (Betty), prize counter in front.
  - **Prize wheel** (north wall) over a stage (Bubble G); **dance machine** (north-east, Boaster); rows of upright
    cabinets (tops reached by pads), a sit-in racing cabinet, a change machine.
- Secret: step behind the curtain of the photo booth (south-east) -> the Hall of High Scores (sealed, under the world:
  Pad Power, Revival, Killer Ducks, Pad shield) -> teleporter back.
- Sightline cover: the claw machine blocks the middle, cabinet rows north, racing cabinet and counters south.
- Sounds: machine hum (fan_pc, transformer, electric_sizzle), occasional bells and buzzers, applause in the high-score
  hall.
