# Starsplash Station (wop_padspace)

An FFA outer-space water park on the moon, human scale (~32u per metre, Padman 56u). x east, y north, park deck z 0,
water z -16. The lunar plain lies 112u below the park's rim wall on three sides, a crater ridge closes the north.
Overhead: stars, the Milky Way, a magenta nebula, a ringed gas giant (south-west) and the Earth rising (south-east),
comets, asteroids and a little flying saucer orbiting high over the park.

Everything but the sky hull and the sealed secret room is detail: 0 portals, BSP + VIS a few seconds, fast light
~40 s, full light (-fast -samples 3 -filter -bounce 2 -bouncegrid) see the Checks section.

- `build_space.py` - the map:
  - **Padstar I** (centre north): a 37 m retro rocket on four fins. Walk in through the door, climb the stair round the
    inside wall to the **cockpit** (consoles, pilot seat, portholes; Visionless), step out of the east/west doors onto
    the **balcony** ring (Jumper). A pad in the ground floor lifts you up through the cockpit floor, a pad in the
    cockpit lifts you into the **nose deck** (**Imperius**, telescope, applause), and a fling pad throws you back out
    through the panorama window onto the plaza. Second ways up: a pad from the plaza onto the balcony and a pad on the
    balcony straight in through the panorama window.
  - Two slides leave the balcony: the **Wormhole** (closed purple tube with glowing rings, portal mouth) sweeps south-west
    over the plaza into Crater Springs, the **Comet Run** (open white/cyan flume) curls east into the Black Hole.
  - **Crater Lagoon** (centre south): an octagonal lagoon (wading ring, deep middle, 16u steps and a regolith beach out of
    the water, moon-rock islets, giant crystal spires) with the **lunar lander "Eagle Pad"** standing on its legs in the
    middle. Jetties north and south lead up stairs to the gold-foil descent stage; walk through the ascent cabin
    (consoles, seat; **Bubble G**); pads from the deck and from the north jetty onto the cabin roof (**Pumper**).
  - **Planet Padurn** (north-west): a banded ringed planet on a crystal pedestal inside a lazy river (48 deep, 16u step
    exits on both banks, two footbridges). Climb the stair bridge from the east up onto the walkable **ring**, take the
    pad up to the icy **polar cap** (**Betty**, applause), fling back down. Three moonlets orbit the planet.
  - **The Black Hole** (north-east): a gravity-well dive bowl - 16u ring steps all the way down so you can walk out
    anywhere - with a rotating accretion vortex on the water and the **Splasher** on the bottom. Beside it the
    **satellite dive tower** (square spiral stair, pad for the bots, diving arm over the bowl, a turning dish, solar
    wings; **Balloony** on top).
  - **Crater Springs** (south-west): a glowing beach pool with a deep crater (Floater), the Wormhole splashdown, two
    **habitat pods** (walk in; pads onto their roofs, Speedy), a moon buggy, a mini rocket, a dish.
  - **Star Boulevard** (east): the **Cosmic Cafe** (googie walls, boomerang canopy, neon, sign pylon with a sputnik
    star; diner tables, stools, jukebox, catalog diner glasses/muffins/coffee pot; **Boaster**; outside stair to the roof
    terrace with parasols), **Mission Control** (consoles, wall screen; BamBam; pad onto the roof with the turning
    radar: Climber), fuel tanks, cargo stacks, canisters, neon posts, a health station.
  - **SECRET**: step into the **Zero-G Loo** between the cafe and Mission Control (flush!) -> **the Star Vault** under the
    world: a starry sky ceiling, crystal heaps, a glowing planet orb, little grey aliens, the golden Padman statue;
    Pad Power, Revival, Killer Ducks, Pad shield, Imperius + Betty ammo; a teleporter back to the boulevard.
  - Plaza: the golden astronaut statue planting the Padman flag, a flag pole, alien bulb trees, crystals, moon rocks,
    dishes, mini rockets, a rover, cargo stacks, signposts, neon posts, a moon-landing film set (catalog camera,
    director's chair, spotlight), loungers and parasols by the water, catalog cacti, ducks, dead aliens, gummy bears.
- `sp_shapes.py` - the convex solids shared by the builder (invisible `common/weapclip` collision) and the models
  (visible surfaces via `splib.solids_mesh`): rocket shell wedges (openings left out), stair, decks, balcony, fins;
  lander stage + cabin; planet sphere frusta, ring, stair bridge; satellite tower + arm; cafe, Mission Control, pods, loo.
- `sp_models.py` - architecture MD3s: the rocket (carved shell with a painted skin, PADSTAR lettering, portholes, chrome
  rails), seats, consoles, the lander, the planet + its stair, the satellite tower, cafe, Mission Control, pods, loo, both
  slides and their entrances.
- `sp_props.py` - props (moon rocks, bulb trees, crystals, neon posts, parasols, loungers, astronaut statue, flag pole,
  dishes, cargo pods, canisters, fuel tank, rover, mini rockets, diner furniture, jukebox, signpost, grey aliens, orb,
  crystal heaps) and IQM movers (comets + asteroids + saucer, moonlets, radar dish).
- `sp_textures.py` - brush textures (regolith, glowing hex deck, deck plate, pool tile with a planet/rocket band, rim
  wall, hull panels, googie wall, gold foil, star floor, signs), the deep-space sky cube `env/padspace/space_*`,
  `padspace.shader`, `wop_padspace.arena` (ffa lps team ft syc_ffa syc_tp).
- `layout.py` - shared constants (rocket profile + openings, lander, planet, bowl, slide paths...).
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padspace_source.zip` into a folder the game sees (for example `wop/zz_padspace.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padspace.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padspace.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padspace.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padspace.bsp

## Checks (Oct 2026)
audit_map OK, check_entities OK, pad_check OK (14 pads, all under 2.4 s), aas_check OK (every pickup reachable, no traps,
19 routes: both jetties, both cabin doors, rocket door + inner stair, both balcony doors, tube mouth, both river bridges,
planet stair, Black Hole steps, satellite stair, pod/cafe/Mission Control doors, cafe stair), sightlines 4.1 % of
eye-level rays over 1800u. 0 portals, full light (-fast -samples 3 -filter -bounce 2 -bouncegrid) 9 min on 2 cores,
BSP 12.6 MB. Bots (10, FFA 5 min): 62 kills, every weapon taken (Imperius 39, Pumper 29, Boaster 25, Balloony 15,
Betty 13, Bubble G 11, Splasher 10), the secret found (Pad Power, Revival, Killer Ducks).
Walk-through: https://claude.ai/artifact/KD4dn14iydraH41w1qZjLk

## Lessons
- The planet ring (a flat `revolve()` drawn outward) faced down and rendered black from above until `inward=True`.
- `carve()` octagons + islet cylinders left ~200 zero-thickness slivers ("duplicate plane"); `drop_slivers()` removes them.
- Pads in/out of the nose window hit the lintel: collision openings are whole 48u wedge layers fully inside the window
  polygon, so the polygon must reach past the layer boundaries.
