# Tilt! (wop_padpinball)

Padman inside a giant pinball machine. Padman scale (catalog models at 1.0). x runs across the table, y runs up the
table toward the backbox, the playfield is z 0 and the playfield glass is the ceiling at z 1088. The table is
mirror-symmetric about x = 0: red owns the west half, blue the east half (CTL, 1-Lolly via the neutral lolly in the
tent, FFA, team, freeze tag, LPS, spray your colour).

Playfield x -1280..1280, y -2432..2432. Everything is detail: 0 portals, BSP+fast light ~35 s, AAS ~1 s.

- `build_padpinball.py` - the map:
  - **flipper end**: apron with instruction cards, two MD3 flippers (weapclip hull), a "flipper shot" kicker in front
    of each (throws you across the table to the other ramp), the drain hole between the flippers, slingshots with a
    rubber face whose kicker trigger bounces you back into play, outlane / inlane guides, kickback pads in both outlanes.
  - **plunger lanes** along both side walls: MD3 plunger on the front wall, a launch pad at its tip that fires you up
    the whole lane (apex 230, ~2600 u/s) to the top arch (Balloony); chasing arrow inserts.
  - **steel ball** (`steel_ball()`): the centrepiece, a chrome MD3 sphere r 144 in a saucer ring; collision is a stack
    of 16-gon weapclip frusta with a flat walkable cap (Splasher), side kickers up to it.
  - **midfield**: standup target banks, a drop-target row, the VUK hole (chrome rim), toys as cover (gummy bears, RC car,
    basketball, rubber islands), the fortune-teller **tent** (`tent()`: doors N/S, neutral lolly inside, toy-block steps
    E/W up to its flat roof).
  - **ramps** (`ramp()`): from midfield up to each raised corner mini-playfield (z 320); a func_rotating spinner over
    the entrance (X axis, nonsolid plate).
  - **corners** (`mini_playfield()`, `booth()`): team prize booth on chrome posts (lolly + health station inside, two
    doors, stairs along the north wall to the roof with the Pumper); Boaster underneath; a kicker from the top lanes.
  - **upper field** (`upper_field()`): three MD3 pop bumpers (cap colour by `_remap`, trigger ring plays a boing),
    rollover lanes, the golden trophy, and the backbox kicker straight up through the hatch.
  - **backbox** (`backbox()`): speaker panel + animated DMD below the glass, backglass art above it; inside: lamp board,
    speakers, MPU box, circuit boards, Imperius + Pad Power, applause on landing, teleporter back to the upper field.
  - **underworld** (`underworld()`): the cabinet interior under the board. The drain drops you onto a steel ramp; coin
    box (Betty + Speedy, secret_found on entry, crate steps to its roof), transformer, speaker, wiring looms, junk;
    teleport pads serve you into either plunger lane (onto the launch pad), the VUK kicker shoots you back up.
  - **arcade room** around the cabinet (seen through the glass): neighbouring cabinets with marquees, neon signs, posters,
    ceiling light panels (they light the table through the glass).
- `pin_models.py` - the MD3 centrepieces (steel ball, pop bumper, flipper, plunger) and their textures/shaders.
- `pin_textures.py` - all textures (original art; the playfield is one 2048 x 4096 painting cut into 2 x 2 tiles fitted
  onto the board), `padpinball.shader` (pulsing inserts with 4 phases, DMD animmap, chrome env maps, glass, glows) and
  `wop_padpinball.arena`.
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, regenerate+compile+audit, preview screenshots.

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh "-fast -samples 3 -filter -bounce 2 -bouncegrid"

## Notes
- A misc_model whose origin ends up outside the world leaks the BSP even though the model itself is inside (the
  catalog duck-tape model has its origin 34u above its base, so placing it on the cabinet floor put the origin under the
  room): watch `Entity N: Entity leaked` in bsp.log.
- Teleporting straight onto a jump pad trips audit_map's "entity inside trigger"; land the player just behind the
  pad instead: Q3 teleports give 400 u/s forward, so they slide onto it.
- The preview now renders `tcGen environment` stages as a sphere-map reflection using the BSP vertex normals (smooth
  chrome on the steel ball, bumper skirts, flipper bolts).
