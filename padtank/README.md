# Fish Tank Temple (wop_padtank)

A Capture the Lolly map inside a giant aquarium at Padman scale (catalog models at 1.0). Two sunken sandstone temples
face each other across the Blue Hole; sharks, a whale shark and schools of tangs and angel fish swim loops around the tank.
Point-symmetric about (0, 0): every red-side piece is built by a function taking `s = +1` (red, west) and rotated 180
degrees for blue (`s = -1`, east).

Tank interior x -2560..2560, y -1216..1212 (reef poster on the back glass), gravel z 0, water surface (ceiling) z 1664.
The whole tank is one fog volume (`padtank/fog`, blue haze, opaque at 4800u) - the "water" is breathable; only the Blue
Hole (r 512, floor -448) is real water. Front and end walls are glass with a dim living room behind them.
Everything is detail: 0 portals, BSP+VIS+fast light ~30 s, full bounce light a few minutes on 2 cores.

- `build_padtank.py` - the map:
  - **temples** (`temple()`): plinth, lolly room with three doors (the front door is the mouth of a stone face with
    glowing team-coloured eyes, brows, nose, teeth), altars, health station, amphorae; outside stairs up the back to a
    landing tower and the roof (Balloony); roof bubble lift to the **filter box** on the end glass (`filter_box()`, Boaster).
  - **causeways**: stone walkway on pillars from each temple roof over the Blue Hole to the ring deck round the spire,
    low posts for cover, stairs down to the gravel on both sides.
  - **centre**: craggy rock spire (Imperius on top, bubble lifts from the ring), neutral lolly on the ring (1LC), tube
    sponges; the Blue Hole with Betty + Pad Power on the bottom and stone steps out of the water under each causeway.
  - **reef** (`reef()`, NW for red / SE for blue): rock mesa with stairs, coral plates spiralling (32u rises, bot barrier
    jumps) up to a perch on a tall stalk (Splasher); a bubble lift from the mesa to the perch too.
  - **diving bell** (`diving_bell()`, SW / NE): an MD3 (`bell_model.py`, misc_model spawnflags 4 = lightmapped,
    `_castshadows 1`): riveted brass body with flared foot, mid and crown bands, ribs, eight raised glass portholes,
    framed west / south hatchways, smooth interior, low walkable riveted dome with a hatch wheel. Collision is invisible
    `common/weapclip` brushes with the same shape (16-gon walls, door gaps, dome frustum r 240 @ 288 -> r 150 @ 316).
    Bubble G inside, coral plates up to the dome and a bubble lift outside the south hatch (Pumper on top).
  - **chests** (`chest()`): mid-lane treasure chests, broken front to walk in (Pad shield), gold-bar steps to the lid.
  - `fish_loops()`: one `func_rotating` per school (origin brush at the circle centre, tiny `nodraw_ns` brush, `model2`
    = an IQM with every fish already placed on the circle, facing its direction of travel and banked into the turn).
    `sweep_check()` samples each school's swept annulus against the solid brushes so no fish swims through scenery.
- `bell_model.py` - the diving bell MD3 + its textures/shaders (uses `../md3write.py`). A full turn holds a whole
  number of texture tiles so wall spans that meet across 0/360 deg have no texture seam.
- `fish_models.py` - procedural leopard shark / whale shark / blue tang meshes plus WoP's catalog angel fish
  (`pad_fish/*.md3`, real shaders), baked into `models/padtank/*.iqm` with `../iqmtool.py`. Tail fins are separate
  single-sided meshes with a `deformVertexes wave` shader, so they wag in game.
- `tank_textures.py` - all textures (original art), `padtank.shader` (caustics stage on stone/gravel/coral, kelp sway,
  bubble sprites, fog, water surface), `wop_padtank.arena` (ctl 1lc ffa team ft).
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, regenerate+compile+audit, preview screenshots.

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc MD3ROOT=~/Games/wop/wop/models.pk3dir ./check.sh

## Why IQM for the fish
MD3 vertices are 1/64 fixed point, so geometry can't sit more than 512u from the model origin. A func_rotating spins its
model2 round the entity origin, so a shark circling 1050u out needs float coordinates. Every WoP renderer (opengl1,
opengl2 - the default - and vulkan) loads static IQMs; opengl2 insists on the tangent array (iqmtool writes it).
Models on movers are lit from the light grid at the entity origin (the circle centre).

## Bot tests (wopded, 10 bots)
- CTL 5 min: ~27 lolly steals, 1 capture, 50 frags.
- FFA 3 min: every weapon taken (Bubble G 30, Balloony 25, Pumper 16, Splasher 5, Boaster 4, Betty 3, Imperius 2).
  Before the mesa->perch lift bots never climbed the 8-plate spiral to the Splasher even though every plate-to-plate
  step checks out in the AAS; the lift fixed it.
