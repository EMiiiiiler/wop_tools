# Padman's Gelato Parlour (wop_padgelato)

An FFA map inside a retro 50s ice cream parlour at Padman scale (~8u per cm, catalog models at 1.0). x east, y north,
floor z 0, ceiling z 2048, room 4608 x 4096. Black and white checker floor, turquoise tiles, cherry-red and cream candy
stripes, chrome. Built on the padbakery helper layer (prop placement by occupied volumes, pads, room shell, street).

Everything but the room shell, the street annex and the sealed secret room is detail: 5 portals, BSP + VIS ~10 s, fast
light ~40 s.

- `build_gelato.py` - the map:
  - **The giant cone** (centre): a triple-scoop waffle cone (vanilla, strawberry, mint with chocolate sauce, a cherry
    and a wafer) in a chrome stand. The **scoop lift** (func_plat, bots ride it) and a pad from the north take you up to
    the wafer rim (**Imperius**, applause). Carton stacks stand round the stand under the overhang.
  - **Gelato counter** (north): eight tubs of gelato behind a glass front with flavour tags; walk on the deck and drop
    into the tubs (ammo inside, 32u barrier jump out). Sugar-cone stairs at both ends, the server aisle behind with
    stock shelves (Visionless), pads from the deck ends up to the high **wall shelf** (**Betty**).
  - **Soft-serve machine** (west wall): walk into the cabinet (**Boaster**), stairs up to the drip-tray deck where two
    swirls turn into giant cones (func_rotating), pads onto the top (**Balloony**) from the deck and from the floor.
  - **Milkshake bar** (east wall): bar stools, a blender spinning, syrups, sundaes, catalog diner glasses; pads up.
    The **giant milkshake glass** stands in front: a pad onto its whipped cream (**Pumper**).
  - **Walk-in freezer** (south-east): through the strip curtain; ice, cartons, Pad shield inside; pads onto the roof
    from the floor and from the bar (**Splasher**).
  - **SECRET**: jump into the **Mystery Flavour** tub in the freezer -> **the Frozen Vault** under the world: ice
    walls, ice-cream ice sculptures, a golden sundae, rock candy, coins; Pad Power, Revival, Killer Ducks; a teleporter
    back to the freezer door.
  - **Chest freezer** (south-west): ice-cube steps up and into it (**Bubble G**), steps back out.
  - **Shop** (south): the ice cream cart with its striped umbrella (pad onto it: Speedy), five topping jars, cafe tables
    with sundaes, the flavour board, the sign over the sunny windows onto the street.
  - Cover: giant display cones, popsicles, sundaes, carton stacks, ice piles, a tasting spoon; catalog gummy bears,
    muffin, diner glasses, coffee pot, a duck, the Padman standee.
- `gl_shapes.py` - convex solids shared by the builder (invisible `common/weapclip`) and the models.
- `gl_models.py` - architecture MD3s (cone, counter + tubs, soft-serve machine, bar, milkshake glass, freezer + Mystery
  tub, chest freezer, cart, topping jars, the swirl movers).
- `gl_props.py` - props (cones, sundaes, banana split, popsicles, cartons, ice, bar stools, blender + blade, syrups,
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

## Checks (Oct 2026)
audit_map OK, check_entities OK, pad_check OK (14 pads, all under 2.7 s), aas_check OK (every pickup reachable; the
scoop lift links as a bot elevator; 10 routes: lift base, both counter stairs, the aisle, the soft-serve cabinet and
stair, the freezer door, the chest freezer in and out), sightlines 3.5 % of eye-level rays over 1800u, 5 portals.
Bots (10, FFA 5 min, fast light): 62 kills, every weapon taken (Imperius 41, Balloony 27, Bubble G 21, Splasher 14,
Pumper 13, Betty 11, Boaster 1), the secret found (Pad Power 5, Revival 2).

## Lessons
- Under a wide overhang (the cone widens upward to r 470 but the stand is r 290 at eye level) long eye-level
  sightlines run straight under it: props round the stand, under the overhang, took sightlines from 4.1 to 3.5 %.
- A pad standing on a deck end blocks a route endpoint there (aas_check "back blocked"); keep route endpoints and pads
  apart.
- Props must fit the shelf gap as well as the shelf depth: a 2-stack of cartons (352u) didn't fit a 240u freezer
  shelf; the occupancy test reports "no room" instead of placing it.
- Sphere/ellipsoid UVs default to one texture tile over the whole sphere: give big scoops u1/v1 repeats or the flavour
  chips come out huge.
