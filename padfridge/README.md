# Midnight Snack (wop_padfridge)

FFA (also LPS, team, FT, SYC) inside a giant open French-door fridge at midnight. Padman scale, built entirely on
`woplib` (the first real map on it). Generator: `wopbuild.py padfridge gen` (or `OUT=<dir> python3 build_padfridge.py`).
Full pipeline: `wopbuild.py padfridge all --light final`.

## Design sheet
- **Theme + scale**: the kitchen at night, the fridge wide open and lit from inside (cool white), the kitchen dim
  moonlight blue. Food is oversized for gameplay (shelves 448u apart).
- **Playable area**: 3456 x 3456 floor plus four stacked levels (floor 0, shelf 1 448, shelf 2 896, freezer 1344).
- **Centrepieces (custom MD3)**: Swiss cheese wedge (shelf 1), milk carton lying on its side (kitchen), two clear crisper
  drawers, the cereal box and two cola bottles standing in the kitchen, the butter compartment (secret door).
- **Zones**
  - *Kitchen floor* between the two open doors: walk through the milk carton (pad onto its roof, Boaster), spilled-milk
    puddle, apple, cereal box, colas, health station.
  - *Crisper drawers* (floor): walk in through the handle cut-outs; the east drawer is pulled out into the kitchen.
    Lettuce, carrots, tomatoes, celery. Splasher inside the closed west drawer.
  - *Shelf 1* (glass): the cheese wedge (tunnel with the Pad shield, walkable 34-degree slope), jelly, yogurt pots.
  - *Shelf 2* (glass): egg box, pickle jars, cake stand. Pumper west, Betty east.
  - *Freezer tray*: frost floor with a slick ice patch, ice cubes, ice cream tub, frozen peas. Imperius (pad only).
  - *Door bins*: three per door. The lower two join shelves 1 and 2 at the fridge front; the top ones are pad-only
    (Balloony east; the butter compartment west).
  - *Back lane* (the airflow gap behind the shelves): chocolate-bar ramp -> butter block -> cracker ramp -> cheese
    stack, floor to shelf 2 on foot; a lift pad from the cheese stack up through the gap into the freezer.
- **Routes**: ramps (floor <-> shelf 1 <-> shelf 2), door bins <-> shelves, jelly pad (kitchen -> shelf 1), shelf-2 pad,
  lift (shelf 2 -> freezer), two pads to the top bins, carton pad. All in `routes.txt` (aas_check).
- **Loot ladder**: Imperius freezer (pad) > Balloony east top bin (pad) / Betty shelf 2 > Pumper shelf 2 > Splasher in
  the drawer > Boaster on the carton roof > Bubble G on the kitchen floor. 3 ammo spots each.
- **Water**: a 12u spilled-milk puddle standing on the tiles (walk straight out).
- **Secret**: walk into the butter compartment in the west door's top bin -> the Deep Freeze (sealed ice cave: Pad
  Power, Revival, Killer Ducks, teleporter back to the kitchen).
- **Sounds**: freezer hum on every level, kitchen clock, crickets outside, dripping milk, icy wind in the Deep Freeze.

## Notes learned here
- bspc traces walk-off ledges only **1000u** down (be_aas_reach.c): the freezer's 1344u front drop gave bots no exit and
  aas_check reported a TRAP. Bots leave over the back edge onto the cracker ramp instead (botclip gap there).
- `revolve()` runs v up the profile while image rows run down: labels on lathe models (cola, tub, yogurt) must be
  flipped vertically (`reg(..., lathe=True)`). Check every label on a `md3sheet.py` contact sheet.
- Ramps 64u off the shelf edges: next to the slab above, the top of a ramp is a crouch-only strip (lint headroom).
- Upper-level sightlines look across the open kitchen between the doors (bin to bin). The cereal box, colas, celery and
  shelf-front cover bring them to 5.5-7.9 %; mapinfo `level_target_pct` records the accepted targets per level, the
  floor keeps 4 %.

## Checks (wopbuild report, final light)
| step | result |
|---|---|
| lint | audit OK, lint OK (0 warnings), every pad lands |
| compile | 0 portals, BSP 2.8 MB, light 57 s (final) |
| aas | every pickup reachable, no traps, 11 routes both ways |
| sight | floor 1.2 %, shelf 1 5.5 %, shelf 2 5.9 %, freezer 7.9 % |
| bots | every weapon picked up, secret found, 42-61 kills in 3 min with 10 bots |
| package | pk3 1.9 MB, pk3_check OK |
