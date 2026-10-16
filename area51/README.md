# Area 51: Dreamland (wop_padarea51)

A free-for-all map: Padman sneaks into the most secret airbase on Earth on a moonlit night. Full-size base at ~64u per
metre, x east, y north, ground z 0, sky hull 5632 x 5120, z -640..2560 (the mothership secret sits below at -2560).
The desert floor is one structural slab with the S-4 lab, its stairwell, the vent shaft and the crash crater carved
out of it (`ground()`), so the underground is sealed by rock and everything else is detail: 34 portals, BSP + VIS in
under a minute, full bounce light ~8 minutes on 2 cores.

- `build_area51.py` - the map:
  - **Hangar 18** (centre north, custom MD3 with arch trusses and hanging lamps): walk in through the big south door, or
    the side and north doors. The **flying saucer** (MD3) stands on three legs inside: walk up the belly ramp into the
    cockpit (Boaster); a pad in the cockpit pops you through the deck hatch onto the saucer (Imperius ammo); a pad on
    the deck throws you through a roof skylight onto the arched **roof** (Splasher). 16u stairs up both side walls to
    the north catwalk (Pad shield, Boomies). Moon-landing film set in the north-east corner (lunar lander + flag MD3s,
    catalog camera and director's chair). A pad outside the east wall also goes to the roof.
  - **S-4 lab** (underground): the freight elevator (`func_plat`) in the hangar's north-west corner goes down to the
    lobby (health station); corridor, autopsy room, xenobiology hall with specimen tanks holding greys (Pumper), server
    passage, and behind a low crawl duct the red **containment vault** (Imperius). Stairs come down from the **S-4
    bunker** (south-west, pad to its roof). A pad in the vent shaft at the corridor's south end throws you back out.
  - **Control tower** (east): walk in, square spiral of 16u stairs to the glass cab (Betty); a pad through the roof
    hatch to the roof (Floater) under the beacon mast.
  - **Water tower** (north-east): a pad onto the catwalk ring, a second pad to the cone roof (Balloony).
  - **Radar station** (west): stairs to the platform under the turning dish (`func_rotating` model2) (Bubble G, Jumper).
  - **Quonset huts** (south-west): walk through both (bunks, lockers, health); pads to the curved roofs (Speedy).
  - **Black triangle** (south-east apron): walk under it or climb the boarding stairs onto it (Pumper).
  - **Crash site** (south): a scorched crater with a crashed scout half buried in it. The hovering scout's **tractor
    beam** (IQM mover, a cow mid-abduction) lifts you from the crashed saucer's dome onto the hangar roof.
  - **Secret**: the drained specimen tank at the south end of the xenobiology hall (secret sound) -> **the
    mothership**: hex-panel bridge with an Earth window, two greys at consoles, a spinning energy core. Pad Power,
    Revival, Killer Ducks, Imperius/Splasher ammo. A teleporter takes you back to the apron.
  - Cover: walk-in shipping containers with crate steps to their roofs, a fuel bowser, fuel tanks, generators,
    humvees, forklifts, crate stacks, jersey barriers, sandbag nests, Joshua trees, cacti, rocks, tumbleweeds;
    floodlight masts (two with turning searchlight beams), runway lights, a UFO circling the sky (IQM).
  - Gate: guard booth (TV inside, pad to its roof), boom barrier, black mailbox, AREA 51 sign; chain-link fence with
    razor-wire posts and warning signs round the perimeter; rock ridges beyond.
- `a51_models.py` - every custom MD3/IQM (procedural meshes, textures, shaders). Kinds: lightmapped (`lm`), lightmapped
  + chrome (`lms`), vertex-lit props (`vl`), glowing (`glow`), alpha cut-outs, glass, glowing liquid, additive beams,
  `dyn` (lightingDiffuse, for movers). The geometry constants at the top are shared with the builder so the weapclip
  collision matches the meshes.
- `a51_textures.py` - brush textures (sand, runway with markings, apron, lab tiles, hazard stripes, signs...), the
  night sky cube `env/padarea51/night_*` (milky way, moon, distant ridge, Vegas glow), `padarea51.shader`,
  `wop_padarea51.arena` (ffa lps team ft syc_ffa).
- `routes.txt` - on-foot routes for `aas_check.py --route` (doors, all stairs, duct, ramp, container steps, crater).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padarea51_source.zip` into a folder the game sees (for example `wop/zz_padarea51.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padarea51.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padarea51.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padarea51.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padarea51.bsp

## Checks (Oct 2026)
audit_map OK, pad_check OK (12 pads, all under 2.6 s), aas_check OK (all spawns placed, every pickup reachable, 23
routes), sightlines 4.2 % of rays over 1800u. 3-minute 10-bot FFA: 37 frags, bots took the vault Imperius, the
water-tower Balloony, the tower-roof Floater and found the mothership (Pad Power, Revival, Killer Ducks).

## Lessons
- Carving rooms out of a slab: a face of a carved piece can be much bigger than the room it bounds (the top of the
  piece under a room runs on under the rock). Pick its texture by sampling many points across the face, not just the
  centroid; q3map2 clips structural faces to the open leaves, so only the room part is drawn.
- sightlines.py only knows catalog models from md3bounds.json; custom MD3s block sight through their weapclip brushes.
  An open airbase needed containers, a fuel bowser and crate stacks in the middle band to get from 14.7 % to ~4 %.
- Wall-mounted text on a cylinder (`watertower()` "51"): u must increase with the angle or it reads mirrored.
