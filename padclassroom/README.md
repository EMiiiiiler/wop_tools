# Padman's Classroom (wop_padclassroom)

Generator: `wopbuild.py padclassroom gen` (or `OUT=<dir> python3 build_padclassroom.py`). Review round: `wopbuild.py padclassroom preview`.

## Design sheet
- Theme + scale: a primary-school classroom on a sunny morning, Padman scale ~8u/cm (catalog models at 1.0); jumbo
  pencils and giant rulers are cartoon-sized so they work as bridges and ramps. Room x -2304..2304, y -1920..1920,
  ceiling 2304. North = the blackboard wall, south = three windows (sky box, sun from the south).
- Centrepieces (custom MD3, cl_models.py): blackboard + chalk-tray ledge, teacher's desk (walk-through knee hole) and
  office chair, a spiral tower of exercise books round an upright jumbo pencil, 4 student desks in a table group
  joined by pencil and ruler bridges, 4 plastic chairs, bookcase (walk-in bottom bay), fish tank on a cabinet with a
  castle ramp and treasure chest, walk-in stationery cupboard with an open door, floor globe (spinning), tipped-over
  bin (walk-in), crayon box (walk-in), pencil case (walk-in, on a desk), lunchbox, radiators, school bags,
  fluorescent ceiling panels, wall clock, paper-plane mobile.
- Levels: floor 0 | chair seats 320 | tank cabinet 400 / tank floor 432 | student desks 560 | teacher desk 608 |
  window sill 720 | chalk ledge 800 | bookcase + tank rim 960 | castle 976 | cupboard top 1600.
- Routes: a giant ruler ramp onto the desk group (W); spiral book stairs onto the teacher's
  desk; pencil (E-W) and ruler (N-S) bridges round the desk group; castle ramp out of the tank onto the bookcase;
  pads: desk group, teacher's desk, ledge (from the desk and from the floor), cupboard top (from the ledge and the desk),
  bookcase, sill.
- Loot: Imperius on the chalk ledge, Betty on the cupboard top, Balloony on the bookcase, Splasher at the bottom of the
  fish tank, Pumper on the teacher's desk, Boaster inside the tipped bin, Bubble G on the desk group. 3-5 ammo spots each.
- Water: the fish tank (488 deep) - the castle ramp walks out onto the bookcase; the chest is the secret.
- Secret: swim into the open treasure chest at the bottom of the tank -> Detention (sealed room under the world, lines on
  the board, Pad Power, Revival, Killer Ducks, Pad shield), teleporter back to the front of the class.
- Sightline cover: the desk group, chairs, bags under the desks, the bin, globe, crayon box, teacher's desk.
- Sounds: wall clock, fish tank bubbler, birds outside on a timer, school bell (door buzzer) on a timer, applause on the
  cupboard top.

## Checks (shipped Nov 2026)
- lint: audit OK, lint OK (10 headroom warnings looked at: under the bin curve, spiral underside, bookcase shelves,
  chair seat backs - none on a route), all 8 pads land.
- compile: 3 portals, no leak; final light (-bounce 2) ~3.5 min on 2 cores.
- aas: 11 routes OK both ways, every pad linked by bspc.
- lights: median 78, 2.4 % dark, 1.2 % bright.
- sight: 4.4 % (WARN, accepted - the floor stays uncluttered; was 14.1 % before the cover pass: chair stack, art
  trolley, toy boxes, gym ball, beanbags, recycling box under the bridges, atlas pile).
- bots (10 bots, 3 min): every weapon picked up (Boaster 22, Bubble G 20, Imperius 15, Betty 10, Pumper 5, Balloony 3,
  Splasher 1), Detention secret found (Pad Power, Revival, Killer Ducks taken), no environmental deaths.
- User change after the preview: the east ruler ramp to the teacher's desk was removed (spiral + pads remain).
