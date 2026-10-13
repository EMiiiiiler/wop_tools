# Countertop Clash (wop_padkitchen)

A Capture the Lolly map on a giant kitchen counter at "army man" scale (~13u per cm, catalog models at ~1.3-1.6).
Mirror-symmetric about x = 0: every red piece is built by a function taking `s = +1` (red, west, negative x) and
mirrored for blue (`s = -1`). Counter tops at z 0, kitchen floor (instant death below z -640) at z -1152, ceiling 2048.

Layout: a U of counters (back counter along the tiled wall y 512..1280, side counters at both ends x +-2176..+-3072)
round a free-standing island (y -1280..-128) with the sink in the middle. The aisle between them is a drop to the floor,
crossed by two cutting boards (x +-1150), a wooden spatula in the middle (neutral lolly, 1LC) and a bread board with a
baguette from each side counter to the island end. Everything is detail: 4 portals, BSP+VIS+fast light ~3 min,
full bounce light ~10 min on 2 cores.

- `build_kitchen.py` - the map:
  - **toasters** (`toaster()`): team base on each side counter, octagonal (chamfered) enamel body with a chrome band,
    three doors, the lolly on a dais between glowing coil walls, health station; two bread slots in the roof you can drop
    through (a toast slice stands in one: pillar inside, cover on the roof), toast-stack stairs (16u) up the wall side,
    Balloony on the roof. Kettle (MD3, team colour) and rolling pin on the side counter.
  - **sink** (`sink()`, `faucet()`): 1280 x 640 basin 448 deep, 48u of soapy water (wading only, bots don't drown),
    cutting-board ramps out at both ends (41 deg, walkable), stacked plates, foam sprites, running water. Betty at the
    bottom; a pad on a plate stack flies you onto the faucet spout (Imperius). The faucet is an MD3 with weapon-clip
    collision (column r 54, spout 112 x 64 flat top).
  - **stove / hood / cabinets**: two lit front burners (blue flame sprites, `trigger_hurt` 15/s), enamel stock pots
    (MD3) on the back burners with pads up to their flat lids (Boaster), range hood whose top joins the two open upper
    cabinets into a high walkway (Splasher in each cabinet, Pad Power on the hood). Pads from the back counter into the
    open cabinets.
  - **back counter**: lying cereal box tunnels (enter through the torn south end or the west hole, sugar cube steps to
    the top; Bubble G inside), cereal spills (MD3), paper towel holder in each corner (pad to the top, Pad shield).
  - **island**: fallen paper towel roll with its sheet as a 23-deg ramp to the top, donut stacks (MD3, weapon-clip
    cylinders), sponge with catalog forks standing in it, cans, dish soap bottle (MD3), Pumper. Flies (MD3 on a
    `func_rotating`) buzz round the donuts.
  - **secret**: a mouse hole at the back of each cereal box tunnel (secret sound + teleport) to the top of the fridge on
    the far wall: Killer Ducks, gummy bears, a cereal box, a pad back down to the island. Bots use it as a flank route.
  - `edge_botclip()`: 24u `common/botclip` strips along every counter edge that drops into the void. Players walk through
    them; the AAS keeps bot paths off the edges. Without them 52 of 61 deaths in a 3-minute CTL bot match were bots
    slipping off the edges; with them 5.
- `kitchen_models.py` - every custom MD3 (procedural meshes + textures + shaders): donuts (drippy icing, sprinkles),
  cereal spills, faucet, stock pots, kettles, dish soap bottle, flies (wings flap with `deformVertexes wave`).
- `kitchen_textures.py` - all textures (original art), `padkitchen.shader`, `wop_padkitchen.arena` (ctl 1lc ffa team ft).
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh` (wopded smoke test + summary), `package.sh` (pk3 + source zip),
  `env.sh` (paths in a cloud session).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padkitchen_source.zip` into a folder the game sees (for example `wop/zz_padkitchen.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padkitchen.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padkitchen.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padkitchen.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padkitchen.bsp

## Bot tests (wopded, 10 bots, 3 min)
- CTL: 11 lolly steals, 2 captures, 32 kills (5 by `trigger_hurt`).
- FFA: every weapon taken except the Boaster on the pot lids (bots rarely take that pad): Pumper 54, Bubble G 38,
  Balloony 20, Splasher 17, Betty 11, Imperius 5; Killer Ducks from the fridge top 15.
