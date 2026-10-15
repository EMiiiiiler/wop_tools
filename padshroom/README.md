# Shroom Trip (wop_padshroom)

A free-for-all map on a forest floor seen through a magic-mushroom trip, at Padman scale (~8u per cm). Giant mushrooms
breathe and shimmer, spores circle the sky, the pond swirls like oil on water and the sky is a violet-to-orange dusk
with aurora ribbons and a slow kaleidoscope swirl overhead (custom sky cube + two additive cloud layers).
x east, y north, ground z 0, sky hull 4864 x 4352, z -512..3200. Playable ground 4096 x 3584 inside steep earth banks
topped with giant grass. Everything except the hull, ground slab and banks is detail: 14 portals, fast compile ~1 min,
full bounce light a few minutes on 2 cores.

- `build_shroom.py` - the map:
  - **Mother Mushroom** (centre): a 1570-tall golden cap (MD3: fibrous stem with blue bruising, drooping ring, umbo,
    96 glowing gill fins). Walk in at the south door: health station, ammo, and a spore-print disc that is a
    `func_plat` elevator (1176u) up to the **gill chamber** inside the cap (Pumper, Pad shield, Boomies; glowing violet
    lamellae walls). A pad in the chamber fires you up through the hatch onto the **plateau** (Imperius). Three
    skylights in the chamber roof drop you back in. Four fling pads on the plateau go to the cottage roof, the stump,
    the pond and the log.
  - **Fly-agaric village** (north-west): the big cottage (walk in: Bubble G, Climber, a glowing toadstool lamp;
    pad from the plaza to the roof: Balloony) and the small cottage (walk in: ammo; a jump pad up to the roof:
    Jumper; a pad on to the big roof). Windows and doors are real holes in the MD3 stems and the collision.
  - **Hollow stump** (south-west): walk in through the root arch; a pad inside shoots you up the hollow through a hole
    in the cut top (Boaster). Two shelf fungi on the bark are walkable ledges (Floater, Boaster ammo).
  - **Fallen log** (south-east): a hollow log you walk through (ramps at both ends, Speedy inside); pads either side
    to the mossy top (Splasher).
  - **Secret**: the tiny glowing door on the north wall inside the log (secret sound + teleport) leads to **the Void**,
    a sealed kaleidoscope room under the world (swirling walls, turning spiral floor, a floating eye on a
    `func_rotating`): Pad Power, Revival, Killer Ducks, Imperius/Splasher ammo. A teleporter takes you back out.
  - **Rainbow pond** (north-east): basin carved out of the ground slab, one water frustum, banks at 35 deg all round
    (walk out anywhere); Betty on the bottom; crystal rocks with a rainbow waterfall; lily pads and a rubber duck.
  - creatures and cover: rainbow snail (MD3), rainbow poison-dart frog (MD3), 16 puffballs, gummy bears, giant nuts,
    spiders, fern thicket (Visionless), sunflowers, flowers, fallen maple leaves, tulips, grass tufts (catalog), a
    fairy ring of glowing bonnet mushrooms round the Mother, spore haze sprites.
  - glowing spores circling the Mother cap: one `func_rotating` with an IQM model2 (they sit 1000-1400u out).
- `shroom_models.py` - every custom MD3 (+ the spore IQM), procedural meshes, textures and shaders. Kinds: lightmapped
  (`lm`), lightmapped + breathing rainbow aura (`lma`), + iridescent env sheen (`lms`), two-sided (`lm2s`), glowing
  (`glow`, with surface light), additive spores. Caps, puffballs and fly-agarics "breathe" with a slow
  `deformVertexes wave` (2-3u, collision unaffected).
- `shroom_textures.py` - all brush textures (original art), the sky cube `env/padshroom/trip_*` (rendered from a
  direction function with the engine's face orientation, so the seams match), `padshroom.shader`,
  `wop_padshroom.arena` (ffa lps team ft syc_ffa).
- `routes.txt` - on-foot routes for `aas_check.py --route` (doors, stairs, arch, tunnel, ramps, pond bank).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padshroom_source.zip` into a folder the game sees (for example `wop/zz_padshroom.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padshroom.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padshroom.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padshroom.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padshroom.bsp

## Lessons
- `revolve()` / `revolve_grid()` take the outward normal from the profile direction: a profile that runs from the axis
  outward over the top of a cap (and back in underneath) needs `inward=True`, or the cap faces down - in game it is
  invisible from above and its lightmap is black. Order profiles bottom-to-top or pass `inward=True` for caps.
- Hollow MD3 buildings on round plans: collision = 16-gon wedge brushes (`ring_seg()`, `stem_shell()`) with the
  outer radius 6-10u inside the MD3; doors/windows are skipped wedges (the MD3 skips the same angular cells, so its
  48-cell grid lines up with the 16 wedges). Faces are textured by their normal: inner faces get the interior texture,
  faces next to an opening get the jamb texture, everything under the MD3 is caulk.
- Door/window frames are tubes: keep the tube centre at MD3 radius + tube radius - a few units, or the frame sinks
  into the wall brushes (audit_map flags it).
- Bot weapon weights matter (WoP botfiles/fw_items.c): Boaster 800 (lightning), Splasher 900, Pumper 1000,
  Betty/Balloony 1200, Imperius 1600. A Boaster on a pad-only roof was never taken in 3 minutes; the Balloony there is.
- A `func_plat` elevator (drawn raised, `height` = travel, a 16u pit at the bottom) gives bspc 60 elevator reachabilities
  and bots ride it to the chamber.
