# Attic Express (wop_padattic)

A model railway in the attic at night, at Padman scale (catalog models at 1.0, ~8u per cm). x east, y north, attic
floor z 0. Gabled roof with the ridge along x at z 1856, knee walls at y +-1792 (256 tall), gable walls at x +-2304.
Mirror-symmetric about x = 0: red owns the west, blue the east (CTL, 1-Lolly via the neutral lolly in the town hall,
FFA, team, freeze tag, LPS, spray your colour).

Everything is detail: 0 portals, BSP+fast light ~25 s, AAS ~2 s.

- `build_padattic.py` - the map:
  - **attic shell** (`hull_box()`, `floor_and_walls()`, `rafters()`): the structural hull's inner faces are the night
    sky (WoP's `env/pf-garden512`, moonlight via q3map_sun from the south), so every window looks out at the night.
    Floorboards, roof boards, exposed rafters, ridge beam, collar beams carrying a plank catwalk (Splasher), ten hanging
    bulbs. Dormer window in the south slope (`carve()` cuts the slope) with a window seat (Boaster) and a telescope;
    square gable windows; a railway poster on each gable wall.
  - **train table** (`table()`): 3328 x 2560 plywood slab, top z 384 with static-grass flock, on legs; the pond is a hole.
  - **track + train** (`ballast_ring()`, `train()`): ballast ring R 928..1072 with eight MD3 track arcs (R 1000). The
    centrepiece train (loco, tender, three carriages) is one IQM model2 on a `func_rotating` with its origin at the
    table centre (9 deg/s, ~160 u/s) and one nodraw collision box per car: players ride on the roofs; anyone standing
    on the track is shoved along it (a rotating pusher moves you on your own radius, so it never pins you).
    `train_sweep_check()` keeps the swept band R 944..1061 clear of static solids.
  - **mountain** (`mountain()`): elliptical papier-mache lower body carved by `carve()` into a railway cutting on both
    approaches and a tunnel bore between 62 and 118 deg; MD3 stone portals (weapclip piers + lintel) and semaphore
    signals at both ends; stairs up to the plateau, kickers up to the snowy peak (Imperius); boulders and pines.
  - **stations** (`station()`): Red Hill (brick, west) / Blue Valley (blue timber, east). The track runs through the
    hall; outer platform holds the team lolly, inner platform the health station; doors on both long walls; stairs to the
    roof (Pumper); roof kicker up to the catwalk. Siding with a parked MD3 loco + carriage, water tower.
  - **village**: town hall in the middle (neutral lolly, clock tower, stairs up to the roof), two cottages per side
    (walk in, stairs up to the 28-degree tiled roof), ship lamps as street lamps.
  - **pond**: 48u deep, sunk into the table at the south; the track crosses on timber trestle wedges with legs; sand
    ramps at both ends.
  - **under the table**: the toy crate with the Betty (gaps in two walls), two train controllers, storage boxes, an
    old suitcase, paint tins, cobwebs, spiders.
  - **attic floor**: crate staircases from the floor to the table at both gable ends, floor kickers onto the table,
    an old trunk per side (book steps in and out, Balloony inside), stored Christmas things, TV, standee, puppet theatre,
    tyre, rolled rug.
  - **hatch** (`hatch()`): the loft hatch drops into the closet below (Pad Power); a kicker shoots you back up.
- `rail_models.py` - MD3s: steam loco, tender, carriage, track arc / straight, three pines, tunnel portal, water tower,
  signal; `train_loop()` bakes the whole train into `models/padattic/train_loop.iqm` on the R 1000 circle.
- `attic_textures.py` - all textures (original art), `padattic.shader` (sky + moon, pond water, glass, cobwebs, glowing
  bulbs / lit windows / clock / signs) and `wop_padattic.arena`.
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, regenerate+compile+audit, preview screenshots.

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh "-fast -samples 3 -filter -bounce 2 -bouncegrid"

## Notes
- Bots ignored every pickup reached only by 32u-riser stairs (Pumper on the station roofs, the catwalk Splasher above
  them, the window-seat Boaster) even though aas_check routes passed; 16u stairs fixed it. Use 32u steps only for short
  climbs (the trunk's three book steps are fine).
- A plaza pocket boxed in by the mountain stairs, a cottage and its stairs was a bot trap (they could drop in, not
  climb out); `aas_check` reports these as TRAP. Leave a 48u+ gap between neighbouring stair flights.
- The pond is 48u deep: walking into it counts as swimming for bots, so its routes stop on the ramps.

## Bot tests (wopded, 10 bots)
- FFA 3 min: 51 kills, every weapon taken (Bubble G 38, Pumper 31, Betty 24, Imperius 14, Boaster 11, Splasher 7,
  Balloony 1). The catwalk Splasher was only taken once the gable-end kickers gave a second way up.
- CTL 5v5 5 min: 77 kills, 31 lolly steals, 4 captures.
