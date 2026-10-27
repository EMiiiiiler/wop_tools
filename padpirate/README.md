# Skull Rock Bay (wop_padpirate)

An FFA pirate water park on a tropical island on a sunny afternoon, human scale (~32u per metre, Padman 56u).
x east, y north, plaza z 0, water z -16. Playable area 4608 x 4096; the open sea (with palm islets and a sailing
ship on the horizon of the custom sky cube) surrounds the park on three sides behind sea walls, a jungle cliff closes
the north. Seagulls circle the bay.

Everything but the sky hull and the sealed secret room is detail: 0 portals, BSP + VIS ~25 s, fast light ~25 s,
full light (-fast -samples 3 -filter -bounce 2 -bouncegrid) see the Checks section.

- `build_pirate.py` - the map:
  - **Galleon Bay** (centre south): an octagonal lagoon (wading ring, deep middle, 16u steps and a sandy beach out of the
    water, rock islets with palms, two wrecked masts sticking out of the water) with **The Salty Padman** anchored in
    the middle. Stone jetties run from the north and south shores to gangway stairs up to her entry ports.
  - **The galleon**: walk the waist (deck guns, barrels, cannonballs), climb the side stairs to the quarterdeck (ship's
    wheel + binnacle) and the forecastle (treasure chest), go into the **captain's cabin** (table, chest, telescope,
    stern windows; Visionless) and the **crew quarters** (Boomies), down the hatch into the **hold** (cannons at the
    gunports, crates; **Bubble G**). A pad on the quarterdeck throws you into the **crow's nest** (**Imperius**,
    applause), a fling pad there drops you on the south promenade.
  - **SECRET**: the giant tipped rum barrel at the back of the hold -> **Captain Padbeard's Hoard** (sealed under the
    world): gold heaps, open chests, Padbeard's skeleton on his throne; Pad Power, Revival, Killer Ducks, Pad shield,
    Imperius + Betty ammo; a teleporter back to the plaza.
  - **Skull Rock** (centre north): a hollow skull wearing a tricorn hat. Walk in through the teeth, climb the stair
    round the inside wall to the **balcony behind the eye sockets** (Pad shield; shoot out through the eyes, which glow
    red), ride the pad up the shaft onto the **crown of the hat** (**Betty**, applause), fling pad back to the plaza.
    The brim is walkable (Jumper) and two slides leave it: the **Cannonball Run** (closed iron tube with bronze bands,
    from a giant cannon muzzle) into Treasure Cove, and the **Plank Plunge** (open wooden log flume) into the Shark Pool.
  - **Fort San Padro** (north-west): curtain walls with merlons, the gate (open doors, raised portcullis), a courtyard
    with stairs up both side walls to the ramparts (cannons), the **powder magazine** in the north wall (BamBam), a pad
    onto the **watchtower** (**Pumper**), and a **mortar** on the east rampart that fires you onto Skull Rock's hat.
  - **Shark Pool** (north-east): a deep dive pool, steps out at the south end, sharks circling under the water, the
    **Splasher** on the bottom; the **walk-the-plank dive tower** (square spiral stair round a mast core, pad for the
    bots, **Balloony** on top, a plank out over the water).
  - **Treasure Cove** (south-west): a beach pool with a deep hole (Floater), the tube slide's splashdown, two bamboo
    **beach shacks** (walk in; pads onto their thatched roofs, Speedy), rowboats, chests, a hammock, palms.
  - **Tortuga Quay** (east): **The Rusty Anchor** tavern (porch, bar with bottles, wagon-wheel chandelier, tables,
    wanted posters; **Boaster**; outside stair to the roof terrace), **Ye Olde Gift Shoppe** (awning, swords and shields;
    pad onto the roof: Climber), market stalls (fruit, fish, rum) on the boardwalk, crate stacks, barrels, the big anchor,
    a capstan, harbour lamps, a parrot on its perch.
  - Plaza: the bronze statue of a pirate captain, cannons, palms, torches, signposts, loungers and parasols.
- `pp_shapes.py` - the convex solids shared by the builder (invisible `common/weapclip` collision) and the models
  (visible surfaces via `pplib.solids_mesh`): the galleon's hull stations (keel to deck, rooms carved out), bulwarks,
  castle rails, stairs, crow's nest; Skull Rock's shell wedges (openings left out), hat, inner stair, balcony; the fort,
  dive tower, tavern, shop, shacks.
- `pp_ship.py` - the galleon MD3s: smooth hull skin (z-mapped strake texture: castles, ochre wale, black, boot-top,
  antifouling), rail caps, transom with gallery windows and name board, gunports with lids and muzzles, wales, stem,
  rubber-duck figurehead, bowsprit, catheads + anchor, decks/interiors from the collision solids; masts with furled
  sails, tops, the crow's nest basket, ratlines, stays, the Jolly Roger.
- `pp_models.py` - every other custom MD3/IQM: Skull Rock + tricorn (carved shell, teeth), fort, dive tower, tavern,
  shop, shacks, both slides + their entrances, cannon, barrels, the secret big barrel, crates, chests, cannonballs,
  anchor, rope coil, rowboat, life ring, palms, parasols, loungers, boulders, torches, lamp posts, ship's wheel,
  capstan, stalls, signpost, wrecked mast, captain statue, parrot, hammock, skeleton throne, gold heaps, bottles,
  table, stool, mortar; IQM movers: sharks, gulls.
- `pp_textures.py` - brush textures (cobbles, sand, planks, deck, boardwalk, coral stone, quay wall, pool tile with a
  rope-and-wave band, timber wall, signs...), the tropical sky cube `env/padpirate/tropic_*`, `padpirate.shader`,
  `wop_padpirate.arena` (ffa lps team ft syc_ffa syc_tp).
- `layout.py` - shared constants (lagoon, hull lines, skull profile and face, fort, pools, slide paths...).
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padpirate_source.zip` into a folder the game sees (for example `wop/zz_padpirate.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padpirate.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padpirate.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padpirate.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padpirate.bsp

## Checks (Oct 2026)
audit_map OK, check_entities OK, pad_check OK (13 pads, all under 2.3 s), aas_check OK (every pickup reachable, no
traps, 25 routes: both gangways, quarterdeck/forecastle/hold stairs, cabin and crew doors, skull mouth + inner stair,
tube mouth, fort gate + both rampart stairs + magazine, dive tower stair, shark pool steps, shack/tavern/shop doors,
tavern stair), sightlines 1.5 % of eye-level rays over 1800u (2.8 % including the decks and ramparts). 0 portals,
full light (-fast -samples 3 -filter -bounce 2 -bouncegrid) 9 min on 2 cores, BSP 12.5 MB.
Bots (10, FFA 4 min): 54 kills, every weapon taken (Bubble G 43, Pumper 25, Splasher 17, Boaster 10, Imperius 8,
Balloony 6, Betty 5), the secret found (Pad Power, Revival, Killer Ducks).
Walk-through: https://claude.ai/artifact/FF3MY1ioWKPDs2qoudJaG2

## Lessons
- The crow's nest Imperius got 0 pickups while its only way up was a pad on the quarterdeck (a cul-de-sac): probe
  triggers (`DEBUG_TRIG=1`) showed one bot visit in 4 minutes. A second pad on the north jetty (on the main route to
  the ship) gave 8-18 pickups per run.
- The crew quarters were a bot TRAP until the capstan in front of the door went: a 30u gap between it and the
  forecastle stairs is not a corridor for bspc.
- The dive tower's square spiral (24u treads) needed the top slab opened two steps early, or the last steps were
  crouch-only for the AAS.
