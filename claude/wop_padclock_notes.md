# wop_padclock (PadClock Tower) - lessons

- A whole tower as one open room measured 22-29 % long eye-level rays per level. Brick partitions along the atrium
  edge lines (doors 192 wide, staggered so no ray passes two doors in a row) plus 64u balustrades round the atrium
  (above the 48u sightline eye height) took it to 2.7 / 3.5 / 3.7 / 5.1 %. Two doors with the same y range on
  consecutive cross walls left a 4000u ray straight along the cuckoo ledge.
- aas_check `--route` is on foot only: a route across a func_plat lift is always "there blocked". Don't add lift routes;
  bspc elevator links + bot runs check lifts.
- `K.stairs16(route=...)` ends its route past the top step in the run direction. A flight that ends beside a roof
  (chime house) needs its own `K.route` onto the roof.
- Rails on pad paths: leave a gap wherever a pad arc crosses a balustrade (pad_check edges only know the floor).
- Free-standing partitions in a 224u band left no launch spot from which bspc's faster arc clears the balcony edge
  above (MID-AIR at the slab underside); those pads went.
- `K.custom` doesn't nudge: place fixed custom pieces (benches) BEFORE the nudged `K.prop`/`K.catalog` scatter, or the
  scatter fills their spot.
- Hanging models (lanterns, weights, chimes, origin at the ceiling point) need a joist or slab exactly above; audit
  reports "100 % of base unsupported" when the ceiling point is open air.
- Upright discs built lying flat: Rx(+a) turns the dial towards -y with the bow on top; Rx(-a) faced it into the wall.
- Bots never took the Pumper at the end of the ledge (stairs + bridge only); a direct pad from the east wing gave 11-22
  pickups per run.
- ~200 MD3s, 37 lit lanterns, 60+ func_rotating hands/gears: final light with bounce 7 min, BSP 11.7 MB, walk-through
  8.8 MB, 504 entities.
