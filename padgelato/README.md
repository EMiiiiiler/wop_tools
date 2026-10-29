# Padman's Gelato Parlour (wop_padgelato)

An FFA map inside a pink 50s ice cream parlour at Padman scale (~8u per cm, catalog models at 1.0). x east, y north,
floor z 0, ceiling z 2048, room 4608 x 4096. Laid out after a reference photo of a real parlour in three bands: the
**seating area** by the street windows (south), the long **mint display counter** with curved glass across the room,
and the **ice cream kitchen** behind it (north). Black/white/grey art-deco floor, pink wainscot and walls, a mint
frieze, a pink tin ceiling, pendant lamps. Built on the padbakery helper layer (prop placement by occupied volumes,
pads, room shell, street).

Everything but the room shell, the street annex and the sealed secret room is detail: 5 portals, BSP + VIS ~10 s, fast
light ~45 s.

- `build_gelato.py` - the map:
  - **Seating** (south): two mint diner booths along the west wall with sundaes on the tables, cafe tables and
    chairs, a glowing **jukebox** (music) by the windows, a gumball machine, balloons swaying, a dog, Padman
    customers, the ice cream cart with its umbrella (pad onto it: Speedy), the flavour board, a shop bell.
    - **The giant cone** in the middle: triple scoop in a chrome stand; the scoop lift (func_plat, bots ride it) and a
      pad take you to the wafer rim (**Imperius**); carton stacks under the overhang.
    - **Milkshake bar** (east wall): stools, the blender spinning, syrups; pads up. The **giant milkshake glass** in
      front: pad onto the cream (**Pumper**).
  - **Display counter** (y 0..300, 2700 long with rounded ends): mint cabinet, pink edge, curved front glass over
    eleven flavour tubs with tags, a walkable flat glass top (Speedy, ammo); pads from the seating side at both ends
    and from the kitchen. A GELATO neon and menu boards hang over it.
  - **Kitchen** (north):
    - **Soft-serve machine** (west wall): walk into the cabinet (Jumper), stairs and a pad up to the drip-tray deck
      where the swirls turn (**Boaster**), pads onto the top (**Balloony**).
    - **Pasteuriser vat**: a steel vat of milk with a paddle turning under the motor bridge; pad onto the rim.
    - **Batch freezer**: PADMAN BATCH 120, the dasher turning behind the porthole; pad onto the top (Visionless).
    - **Prep line** (north wall): eight tubs being filled behind glass, pads onto the deck and on to the high **wall
      shelf** (**Betty**); the server aisle behind; five topping jars in front.
    - **Walk-in freezer** (east wall): through the strip curtain; ice, cartons, Pad shield; pads onto the roof
      (**Splasher**).
    - **Chest freezer** (north-east): ice-cube steps up and into it (**Bubble G**).
  - **SECRET**: jump into the **Mystery Flavour** tub in the walk-in freezer -> **the Frozen Vault** under the world
    (golden sundae, ice sculptures, coins; Pad Power, Revival, Killer Ducks); a teleporter back to the freezer door.
- `gl_shapes.py` - convex solids shared by the builder (invisible `common/weapclip`) and the models.
- `gl_models.py` - architecture MD3s (cone, display counter with curved glass, prep line, soft-serve machine, batch
  freezer + dasher, vat + paddle, bar, milkshake glass, freezer + Mystery tub, chest freezer, cart, topping jars,
  the swirl movers).
- `gl_props.py` - props (booths, jukebox, gumball machine, balloons, dog, hanging neon/menus, cones, sundaes, banana split, popsicles, cartons, ice, bar stools, blender + blade, syrups,
  cone stacks, spoon, ice sculptures, golden sundae) plus the reused bakery furniture (tables, chairs, lamps, fans...).
- `gl_mesh.py` - mesh helpers + model textures (ten gelato flavours, waffle, sleeve, enamel, cart, frost...).
- `gl_textures.py` - brush textures (checker, turquoise tile, stripes, cone frieze, chrome trim, ice wall, flavour
  board, signs), `padgelato.shader`, `wop_padgelato.arena` (ffa lps team ft syc_ffa syc_tp).
- `layout.py`, `routes.txt` (generated), `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh`.

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padgelato_source.zip` into a folder the game sees (for example `wop/zz_padgelato.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padgelato.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padgelato.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padgelato.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padgelato.bsp

## Checks (Oct 2026, three-band layout)
audit_map OK, check_entities OK, pad_check OK (19 pads, all under 2.7 s, 19 bspc jump pad reachabilities), aas_check
OK (every pickup reachable; the scoop lift links as a bot elevator; 6 routes: lift base, soft-serve cabinet and stair,
the aisle, the freezer door, the chest freezer), sightlines 2.6 % of eye-level rays over 1600u, 5 portals. Bots (10,
FFA 5 min): 90 kills, every weapon taken (Imperius 73, Boaster 23, Balloony 19, Bubble G 10, Splasher 9, Pumper 8,
Betty 4), the secret found (Pad Power 2, Revival 2).

## Lessons
- The Boaster in the soft-serve cabinet (a dead end at the wall) got 1 bot pickup in 5 min although reachable; on the
  drip-tray deck (stairs + pad, on the way to the top pads) it got 12.
- Under a wide overhang (the cone widens upward to r 470 but the stand is r 290 at eye level) long eye-level
  sightlines run straight under it: props round the stand, under the overhang, took sightlines from 4.1 to 3.5 %.
- A pad standing on a deck end blocks a route endpoint there (aas_check "back blocked"); keep route endpoints and pads
  apart.
- Props must fit the shelf gap as well as the shelf depth: a 2-stack of cartons (352u) didn't fit a 240u freezer
  shelf; the occupancy test reports "no room" instead of placing it.
- Sphere/ellipsoid UVs default to one texture tile over the whole sphere: give big scoops u1/v1 repeats or the flavour
  chips come out huge.
- A motor beam across a vat blocks any pad landing that flies along it: turn the beam perpendicular to the pad's
  approach (the vat beam runs north-south, the pad comes from the east).
- A 44u gap between the prep line end and the chest-freezer steps left no AAS area at the foot of the steps; keep
  48u+ in front of any stair foot (prep line narrowed to x +-1300).
