# Padman's Little Cake Shop (wop_padcakeshop)

Generator: `wopbuild.py padcakeshop gen` (or `OUT=<dir> python3 build_padcakeshop.py`). Full pipeline: `wopbuild.py padcakeshop all`.
Models: `ck_models.py` (every custom MD3, its textures and its weapclip collision).

## Design sheet
- Theme + scale: a small pastel cake shop at Padman scale (~8u/cm, catalog models at 1.0). Pine display unit from the
  user's reference photo, mint/white boarding, pink facade with a striped awning outside. Indoor, daylight through the
  window and the open door; sky `env/fort-pad512` over the pavement.
- Playable area: shop x -1920..1920, y -1536..1536 (floor 0, ceiling 1792) + the pavement y -2112..-1600 outside
  (road beyond the kerb is scenery behind `common/clip`). Bounds in mapinfo = playable, hull = sky box.
- Centrepiece (custom MD3): the four-shelf pine display unit (shelves 96 / 400 / 704 / 1008) with cakes, trays of
  bakes and the tiered cupcake stand on top (recessed plinth under the bottom shelf).
- Landmark zones (each enterable and climbable):
  1. Display unit: 16u sugar-cube steps to shelf 1, pads to shelves 2/3 from the cake boxes, pad_unit to the top,
     pad_tier onto the cupcake stand (summit, applause).
  2. Counter + espresso machine (west): no walk-up ramp (user); open coffee-bean sack with pad_sack beside it, plus
     pad_counter; pad_espresso from the counter and pad_unit_esp from the unit top onto the machine's deck (1160).
     Staff aisle and cubbies behind/under the counter (Floater).
  3. Bread rack (east wall): three tiers by pad_rack1/2/3.
  4. North wall shelves: low shelf 944 (bread-board bridge from the unit top, pad_shelf from the floor), high shelf
     1360 (pad_shelf_hi from the low shelf, pad_unit_shelf from the unit top), cookie jar below its east end.
  5. Window display (520): pad_window; planter, bread basket, teapot, tulip, cake stand, boxes only (nothing that melts).
  6. Bistro table (600): pad_table.
  7. Outside: pavement, bench, planters, A-board; pad_awning onto the awning top (1352). The door is open; the area
     just inside the door is deliberately empty (user).
- Routes (routes.txt, aas_check both ways standing): unit_steps (floor -> shelf 1), bridge (unit top -> low wall
  shelf), cubby (staff aisle -> counter cubby).
- Loot ladder: Imperius (1600) on the tiered cupcake stand (two pads); Betty (1200) on the high wall shelf
  (x -40, between the two pad landings); Balloony (1200) on the espresso deck; Pumper (1000) bread rack top tier;
  Splasher on the awning; Boaster on the bistro table; Bubble G on the shop floor. 4 ammo spots each (mix of open
  floor, shelves, cubbies and the street), Nipper ammo x3.
  Other: Padshield on unit shelf 2, shards (low shelf, rack, window), Speedy (window), Jumper (rack top), Floater
  (counter cubby), Visionless (behind the door), health station NE corner.
- Water: none.
- Secret: the cookie jar on the low shelf, open only from above (walk off the east end of the high shelf) ->
  trigger_teleport into a sealed cookie vault below the world (Pad Power, Revival, Killer Ducks, Padshield) with a
  teleporter back to the shop floor.
- Sightline cover: floor props (sugar sacks, milk churn, coffee sacks, cake boxes, flour sacks, bonsai, planters),
  the bistro set, the plinth under the display unit. No food on the floor.
- Sounds: espresso machine `ambient/slime_bubbling`, `machine/clock_ticking` on the north wall, `animal/blackbird`
  outside, timed `misc/bicycle_bell` and `animal/kitten_meow`, doorbell `machine/dingdong` on the door,
  `human/applause` on the cupcake-stand summit, `misc/secret_found` at the jar.

## Checks
Final build (13 Nov 2026). Lighting was softened after the first final build washed out every top near the ceiling grid: `_ambient` 60, grid 2000 at z 1560, pendants 300/450.

Definition of done: every step PASS (WARN = looked at and accepted). **DONE**

| step | status | numbers |
|---|---|---|
| quick | PASS | seconds: 1; page_mb: 3.3 |
| gen | PASS | seconds: 3 (was 4); warnings: 0 |
| lint | WARN | lint_warnings: 2; audit: OK; lint: OK; pads: OK |
| compile | PASS | portals: 4; bsp_mb: 5.4; light: -fast -samples 3 -filter -bounce 2 -bouncegrid; seconds: {'bsp': 1, 'vis': 0, 'light': 148, 'bspc': 1}; reach_areas: 1570 |
| aas | PASS | routes: 3; problems: 0; pads_unlinked: 0 |
| lights | PASS | median: 107 (was 100); dark_pct: 0.2; bright_pct: 3.1 (was 5.9) |
| sight | PASS | long_ray_pct: 3.4; target: 4.0 |
| bots | PASS | kills: 54 (was 56); minutes: 3; bots: 10 |
| render | PASS | walkthrough_mb: 4.7; screenshots: 41 |
| levelshots | PASS | files: 5 |
| package | PASS | pk3_mb: 3.5; source_mb: 1.5 |
