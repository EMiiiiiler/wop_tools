# Padman's Garage (wop_padgarage)

FFA (also LPS, team, FT, SYC) in a suburban double garage at night, two roller doors half open onto a moonlit
driveway. Built on `woplib` + `texlib`. Generator: `wopbuild.py padgarage gen` (or `OUT=<dir> python3 build_padgarage.py`).
Full pipeline: `wopbuild.py padgarage all --light final`.

## Design sheet
- **Theme + scale**: Padman scale, ~6 u/cm (1 m = 600u), catalog models at ~1.0 (paint tins, tyre, extinguisher match).
  Cold fluorescent strip lights inside, a warm street lamp and blue moonlight outside.
- **Playable area**: garage interior 3600 x 3600 (x -1800..1800, y 0..3600), driveway 3600 x 2400 (y -2400..0),
  side alleys ~470 wide east and west, all inside a sealed sky hull (fences + hedges + neighbours' trees outside).
  Levels: floor 0, car cabin 160, car roof ~790, workbench 540, shelving 400 / 800 / 1200, loft 1456, garage roof
  (gable, 22 deg, ridge 2200).
- **Centrepiece (custom MD3)**: a 1960s station wagon on axle stands in the west bay, driver's door open, rolling
  work stairs up to the door. Smooth lofted body, chrome bumpers, whitewall tyres, glass, seats, dash.
- **Zones**
  - *West bay*: the car on axle stands (200u clear under the body, spare-parts boxes and trouble lights), walk in through the open door
    (seats, steering wheel, glovebox), pad from the car roof up to the loft.
  - *Centre aisle*: engine hoist with an engine hanging from the chain, a lawnmower, a stack of tyres, the mechanic's
    creeper, the drain grate.
  - *East bay workshop*: workbench along the east wall with a vice, a gooseneck lamp and a pegboard of tools; a red
    rolling toolbox with open drawers; the chest freezer near the front with a tight gap behind it.
  - *Back wall*: steel shelving (three walkable shelves) full of paint tins, boxes and jars; a plank ramp leaning
    from the floor up to the first shelf.
  - *Laundry corner* (back west): washing machine leaking a puddle, concrete laundry tub full of soapy water
    (steps inside: washboard + soap), mop bucket, detergent.
  - *Loft* (back third, over the rafters' bottom chords at 1440): Christmas boxes, tent bag, sleeping-bag rolls,
    a chilly bin, fishing rods. Ladder for players, pads for bots.
  - *Driveway*: an aluminium dinghy on a trailer (plank ramp up into the boat, boxes stored under it), a box trailer
    of garden-waste bags, wheelie bins, hose reel, wheelbarrow, rain barrel at the door pier, street lamp, basketball
    hoop over the doors.
  - *Side alleys*: east alley with the side door into the workshop; west alley with a lean-to woodshed: pad onto its
    roof (800), then a pad onto the garage roof (bspc's 3 s flight can't clear the eave from the ground).
  - *Garage roof*: walkable gable, ridge walk 4u proud, nothing blocking shots.
- **Routes**: roller-door gap (driveway <-> garage), side door (east alley <-> workshop), rolling stairs (floor <->
  cabin), plank ramp (floor <-> shelf 1), boat drawbar (driveway <-> boat), laundry-tub steps (in/out of the water);
  pads: car roof, loft (from the car roof), workbench, shelf 3, washing machine, woodshed, garage roof (from the shed),
  ridge fling pad back down to the driveway.
- **Loot ladder**: Imperius loft (pad/ladder) > Betty bottom of the laundry tub > Balloony top shelf (pad) > Pumper car
  roof (pad) > Splasher in the car cabin > Boaster behind the chest freezer > Bubble G in the dinghy. 3-4 ammo each.
  Pad shield in the crawl space under the car, shards on the garage roof and the workbench.
- **Water**: laundry tub (deep, 16u steps inside up to the rim, the rim reached from the washing machine) and a 12u
  puddle on the floor (walk out). The mop bucket's water is a model surface (no volume).
- **Secret**: walk into the car's glovebox -> the Sewer Den (sealed, below the world): a rats' hangout with a sardine
  -tin bed, bottle-cap table and a sewer lamp; Pad Power, Revival, Killer Ducks; you leave by popping up out of the
  drain grate in the garage floor.
- **Sightline cover**: a brick pier splits the door into two; engine hoist, mower, two rolling toolboxes, tyres,
  freezer, boxes under the car in the garage; boat (boxes underneath), box trailer, bins, tyres, rain barrel on the
  driveway. Floor 4.0 % of rays over 1800u; the car roof / loft / garage roof levels look across the open garage
  and out of the doors on purpose (targets 10 / 12 %, mapinfo `level_target_pct`).
- **Sounds**: fluorescent hum (machine/transformer), dripping (ambient/water_drippling) at the washing machine,
  crickets and an owl outside, a dog barking on a timer, secret_found.

## Checks
wopbuild `all --light final` (Nov 2026): lint/audit OK, 0 portals, aas 12 routes OK + every pad linked where intended
(pad_aas), lights median 77 / dark 5.3 % / bright 3.8 %, sightlines floor 4.0 % (upper levels 9.6 / 11.7 % vs 10 / 12),
bots 3 min x 10: every weapon picked up (Pumper 20, Imperius 19, Boaster 17), 0 falling deaths; the two armor shards
(roof ridge, bench) and Balloony/Imperius ammo are rarely taken by bots. pk3_check OK, pk3 3.4 MB.
