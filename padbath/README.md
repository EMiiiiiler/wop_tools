# Battle in the Bathtub (wop_padbath)

A Capture the Lolly map in a giant bathtub. Two toy battleships anchored at the ends of the tub are the team bases;
toy ferries shuttling between them are the main way across. The map is point-symmetric about (0, 0): every red-side
piece is built by a function taking `s = +1` (red, west) and rotated 180 degrees for blue (`s = -1`, east).

Tub interior x -2496..2496, y -1088..1088, water surface z 0, tub floor -320, enamel rim z 320, ceiling 1664.
Three tiled walls with a duck-tile border, a pleated shower curtain on the south side. Single structural box,
everything else detail: 0 portals, VIS instant, fast light ~15 s, full bounce light a few minutes on 2 cores.

- `build_padbath.py` - the map:
  - **ships** (`ship()`): floating hull (96u draft, botclip block underneath so bots never route under it), deck z 128, bridge house with three doorways and the team
    lolly inside, outside stairs to the bridge roof (Balloony), fore/aft gun turrets climbable by ammo-crate steps,
    funnel, mast + waving flag, lifebuoys, name board, health station, stern boarding ramp out of the water.
    A roof pad flies to a glass shelf on the end wall (Boaster, bath clutter).
  - **ferries** (`ferry()`): two `func_bobbing` toy boats (x axis, height 1278, period 16 s, phases 0 / 0.5) run
    between landing piers on each ship's inboard side. Hull = one entity with a flat top; the open wheelhouse is a
    second func_bobbing with the same keys (see the bot notes below).
  - **shuttles** (`shuttle()`): the third route. A low red / blue shuttle (deck z 48, period 10 s) runs from a stage
    in front of each ship (stairs down from the deck) to a stage on the hub, so a crossing is ship -> hub -> ship.
    The main ferries ride on the surface (no draft) so the hub's diagonal ramps can dip under their lanes.
  - **centre**: rainbow ring stacker standing on the tub floor, shuttle stages east/west, ramps out of the water on
    the 45/225 deg faces, pads (135/315 deg) to the top (Imperius), killer ducks on the first ring, neutral lolly (1LC).
  - **north / south**: bar of PADSOAP / sponge (same shape, chamfered ramps at both ends, Bubble G + Pad shield,
    pad up to the rim). Above them the tap spout and the rain shower head, both perches reached by a rim pad (Splasher).
  - **tub floor**: drain (Betty) under the north lane, plug on its chain (Pad Power) under the south lane - open water
    above both, so bots surface straight up.
  - suds islands with rubber ducks (Pumper, ammo), anchored marker buoys, shampoo bottles, toothbrush cups, deo cans,
    towels, sponges and razors on the rim, sunken soft ball and fish.
  - `carve_water()`: the water box is CSG-carved around every solid in it (`wopmap.carve`), only the surface faces
    are drawn (`water_inner` = nodraw water for the faces between pieces).
- `bath_textures.py` - every texture (original art), `padbath.shader`, `wop_padbath.arena` (ctl 1lc ffa team ft).
- `../mover_sweep.py` checks every func_bobbing's swept path against static brushes (run it after moving anything).
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, regenerate+compile+audit, preview screenshots.

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh "-fast -samples 3 -filter -bounce 2 -bouncegrid"

## Bots and func_bobbing ferries (what it took)
- bspc links a func_bobbing to every grounded area within 192u of the mover's outline at each end (end not more than
  32u above / 128u below). The link plane is the top of the mover's model bounds + 24, so the hull model must be flat
  at deck height: a cabin, rail or funnel on the same entity lifts the plane and no links are made. Put superstructure
  on a second func_bobbing with identical height/speed/phase/spawnflags.
- botlib boards only while the bob is within 16u of its start and gets off only while it is within 24u of its end
  (about 1 s each with a 16 s period), walking between the dock edge and the hull's centre. Keep the ferry short
  (256u), keep the deck centre clear, and dock against a clean pier exactly as wide as the boat: every other area near
  the end position becomes a link whose start/end the bot cannot reach in time, and bots then ride back and forth.
- Bots drown under big low ceilings over water (they push up for air after ~6 s and stay stuck). The piers and tower
  stand on the tub floor; under each floating ship hull and stern ramp a `common/botclip` block fills the water.
- `../aas_check.py` now prints each team's capture run (own spawns -> enemy lolly -> home) with the travel types used.
- 5v5 bots for 7 minutes: lollies stolen 20-30 times, captures 0-1 (carriers die waiting at the enemy pier);
  bots ride the ferries ~15% of the time, swim to the centre toys a lot.
- Third route test (shuttles via the hub, 7-min 5v5 matches): shuttles carried 35-45% of all rides, but captures
  stayed at ~1 per match (baseline 1.5, n=2 vs 3 runs - noise). Most carriers die within 3 s of the pickup, so spawns
  were moved out of the lolly room; carriers that survive often can't score because their own lolly is out too.
