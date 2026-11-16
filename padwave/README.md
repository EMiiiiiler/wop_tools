# Padman's Wave World (wop_padwave)

Generator: `wopbuild.py padwave gen` (or `OUT=<dir> python3 build_padwave.py`). Full pipeline: `wopbuild.py padwave all`.

## Design sheet
- Theme + scale: indoor water park under a glass barrel vault (human scale ~64 u/m, catalog props 0.3-0.9), plus the
  open-air Volcano Bay annex through two arches in the north wall.
- Playable area: hall 4480 x 3456 + annex 3200 x 2080 (bounds -2240,-1728 .. 2240,3840).
- Centrepieces (custom MD3): Twister Tower with the purple Sky Screamer (loop) and blue Twister helix, the five-tier
  volcano with the Lava Chute flume and waterfall, the vault ribs/glazing, the blimp orbit (func_rotating IQM).
- Landmarks (enterable + climbable): Twister Tower (3 decks + crow's nest), Banana Hut on the sun terrace, Surf Shop,
  lifeguard tower, The Plank dive tower, Tiki Bar, Mount Kaboom (5 tiers).
- Loot ladder: Imperius crow's nest (pad); Betty volcano summit + deep-end floor at the intake; Balloony Banana Hut
  roof (pad); Pumper lifeguard roof (pad); Splasher Coconut Island + river; Boaster tower L2 + Tiki Bar; Bubble G
  promenade + east beach. 3-6 ammo spots each.
- Water + exits: wave pool (beach ramp), lagoon and plunge pool (16u steps), lazy river (steps on every straight).
- Secret: underwater wave-machine intake in the deep end's south wall -> sealed pump room (Pad Power, Revival,
  Killer Ducks, Pad Shield) -> teleporter back to the beach.
- Sightline cover: carts at the beach ends and in front of the tower, a rock on the promenade; the wave pool itself
  stays open (sight WARN ~5.5 %, accepted).
- Sounds: water_rippling/flowing speakers, applause triggers on the nest and crater, lava bubbles, crowd timer.

## Checks
(wopbuild writes report.md in the build folder; paste the summary here when the map ships)
