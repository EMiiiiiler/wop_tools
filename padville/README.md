# Padville Junction (wop_padville)

Generator: `wopbuild.py padville gen` (or `OUT=<dir> python3 build_padville.py`). Full pipeline: `wopbuild.py padville all`.
Models: `pv_models.py`. New shared modules written for this map: `woplib/town.py` (walk-in climbable buildings) and
`woplib/railway.py` (track rings, ridable circle trains, turntables).

## Design sheet
- **Theme + scale.** A hobbyist's model railway in a basement, at two scales. On the layout (x < 1152) you are a model
  figure: 48u per model metre, so buildings, the train and trees are life-size. On the workbench (x > 1152) everything
  is giant: 42u per real centimetre, so the mug is 400u and the ruler is a ramp. Catalog props: trees/cars at ~0.6-0.85,
  bench things (paint tins, pencils, thread spool, nut) at ~3-5x.
- **Playable area.** 5120 x 4096 (x -2816..2304, y -2048..2048). Floor 0. The basement ceiling is at 2600.
- **Edges.** A painted scenic backdrop runs along the north and west walls. On the open south edge there's an acrylic
  safety guard with player clip above it, and past it the dim basement is painted on the far wall.
- **Centrepiece.** The Padville Express is a loco plus 3 coaches (one IQM on a func_rotating), circling R 1500 round
  (-832, 0) at 6 deg/s. You can ride on the roofs. The tunnel roof is car top + 90, so riders never wedge the train.
- **Zones** (each one can be entered and climbed):
  - **Padville station** (2 storeys, stairs to the roof). Curved inner and outer platforms with step bands. Walkable
    canopy that you reach by jumping out of an upper window.
  - **Church** (nave with pews, gable roof via a pad) and **tower**. A lift pad inside the tower goes up through the
    roof hatch to the Betty.
  - **Shop row:** bakery, toys, post office. Awnings, stairs, roof via an internal flight. Two **houses** with gable
    roofs, ridge walks and pads.
  - **Lake** with 16u steps out and a **water mill** whose wheel turns in the water.
  - **Mountain:** three rock tiers (400 / 640 / 832). The tunnel is bored through T1 with stone portals. 16u stairs
    lead up the NE side and between the tiers, plus pads. The Balloony is on the snowy summit.
  - **Farm:** barn with a hayloft and a turning windmill. **Goods yard** with a shed and a signal box (outside stairs).
  - **Engine shed** with a parked loco. **Turntable** you can ride (func_rotating deck over a 16u pit; bots walk the
    pit floor).
  - **Workbench:**
    - tipped-over mug you can walk into, with a spilled-coffee puddle
    - controller box reached by the ruler ramp
    - desk lamp: pad from the controller onto the shade, Imperius on top
    - walk-in station kit box with sprues inside
    - screwdriver, glue tube, battery, paint tins, thread spool
    - pegboard shelf (Pad shield + Speedy) reached by pad
  - **Underworld** under the town (z -600, between the joists, wiring and point motors). Drop in through the H1
    access hatch on the plaza; a lift pad under the H2 hatch takes you back up.
- **Loot ladder:**

  | Weapon | Where |
  |---|---|
  | Imperius | Lamp shade |
  | Balloony | Summit |
  | Betty | Tower roof |
  | Pumper | Underworld |
  | Splasher | Lake bed |
  | Boaster | Plaza |
  | Bubble G | Station platform |

  Each weapon has 4-5 ammo spots, some hidden (tunnel niche, mug, kit box, underworld) and some in plain sight.
  Health stations: platform, bench, farm.
- **Secret.** A refuge niche halfway through the tunnel has a fake rock back wall. Behind it, a passage teleports you to
  the "spare-parts tin" vault with Pad Power, Revival and Killer Ducks. The exit teleporter drops you on the bench.
- **Basement corner** (behind the acrylic, decorative): modelled wooden stairs up to the house door on a landing,
  washing machine + laundry basket, hot-water boiler with copper pipes, metal shelving with labelled boxes under a high
  window with an additive sunbeam, bucket + mop. Replaced the painted wall in round 2.
- **Themed jump pads** (`K.jumppad(dress=...)`): manhole covers in town, steam vents on the mountain, a trapdoor in
  the tower, a coil spring under the board, the controller's red push button, a sewing button on the bench.
- **Sounds:** trains (mechanics, horn on a timer), level-crossing bell, church bell, clock in the station, water at the
  fountain/mill/lake, transformer hum + sizzle underneath, blackbird.

## Checks (fast-light build, Nov 2026)
- lint/audit OK; 9 portals; AAS: every pickup reachable, 37 routes both ways, all 13 pads linked
- lights median 88, 3.4 % dark, 1 % bright
- sight: ground level 3.5 %; upper level (roofs, tiers, bench tops looking across the room) 7.6 %, target relaxed to 9
- bots (10 bots, 3 min FFA): 43 kills; every weapon picked up; secret vault items taken
- Boaster ignored by bots inside the mug (dead end, weight 800): it moved to the plaza and the mug got ammo + a shard
