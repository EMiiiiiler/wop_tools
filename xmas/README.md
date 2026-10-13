# Padman's Christmas (wop_padxmas)

A living room on Christmas Eve at Padman scale (about 8u per cm, so catalog models sit at their native scale 1.0).
Room x -2176..2176, y -1792..1792, ceiling 2112; a snowy roof terrace above the fireplace and a snowy garden behind the
window (sky `env/frost-bite512`). 3 portals, VIS instant, fast light ~30 s, full bounce light a few minutes on 2 cores.

- `build_xmas.py` - the map:
  - **the tree** (centre-north): stand + trunk, 5 stacked fir tiers (16-gon frusta) with necks, baubles under every lip,
    blinking bulbs, tinsel drapes, a spinning star (func_rotating, nonsolid). Presents under the lowest boughs, placed by a
    small overlap-free placer (opened ones hold loot). Jump-pad chain: 4 floor pads -> tier 1 -> 4 pads -> tier 2 -> 2 pads
    -> tier 3 -> 2 pads -> tier 4 -> 1 pad -> the top. Loot gets better with height: Bubble G + shards, Boaster + Pad shield,
    Splasher + Speedy, Betty + Visionless, Imperius + Pad Power on top. One outward "fling" pad per upper tier gets bots
    (and anyone in a hurry) back to the floor - bspc gives no walk-off links from the steep skirts.
  - **fireplace** (west): brick breast, mantel (hearth pad) with candles, clock, nutcrackers, cards, stockings, garland;
    nonsolid logs + fire sprites; walking into the flames teleports you up the chimney to the **roof terrace** (secret
    jingle): Santa's sleigh (step in at the back), reindeer, sack, snowman, teleporter home.
  - NW armchair, side table (cocoa, walnuts, pipe, poinsettia), floor lamp, grandfather clock with a func_pendulum.
  - NE sideboard (pad): rotating Christmas pyramid, snow globe, nutcrackers, advent calendar, wreath.
  - East sofa (pad to the seat, pad to the back), coffee table with an Advent wreath (3 candles lit).
  - SE gingerbread house: walk in through the door, candy-cane ramp (players) or pad (bots) onto the 30 deg iced roof.
  - South window seat (pad) with a view of the snowy garden, curtains, bells; SW rocking horse, drum, Santa's sack;
    centre toy train on an oval track around a present tower; present stacks everywhere as cover.
- `xmas_models.py` - every big piece as an MD3 (original geometry, built with `../meshlib.py`): the whole tree (stand,
  trunk, five layered tiers of drooping boughs with interleaved tips, walkable rings, baubles, a light chain with
  blinking bulbs, tinsel swags, star pole), the spinning star, every present (one MD3 per size/paper: rounded box,
  raised satin ribbons, looped bow; opened boxes with folded flaps and tissue), carved mantel with corbels and fluted
  pilasters, gilt picture frame, fire basket + logs, stockings, garland, candlesticks, nutcrackers, mantel clock, fire
  tools, stool, wingback armchair, footstool, side table, floor lamp, sofa, coffee table, sideboard, grandfather clock,
  Christmas pyramid (static base + rotating carousel), snow globe, poinsettia, wreaths, Advent wreath, curtains, rod
  with bells, window-seat cushion and pillows, gingerbread house (walls, gables, iced roof with drips and gumdrop tiles,
  candy-cane posts, iced windows), candy canes, gumdrops, chocolate table, gingerbread men, Santa's sleigh, sacks,
  reindeer (one Rudolph), rocking horse, drum, train track, engine and wagons, paper stars and mistletoe.
  All lightmapped (misc_model spawnflags 4) with shadows; collision is invisible weapon clip in the old brush shapes
  (`with as_clip():` in build_xmas.py), so jump pads, routes and bot paths are unchanged. Models taller than 1024 are
  stored round their mid-height and placed with modelscale 2 (`save_md3(with_offset=True)`).
- `xmas_textures.py` - every texture (original art), `padxmas.shader`, `wop_padxmas.arena` (shares helpers with playroom).
  The model shaders are appended to `padxmas.shader` by build_xmas.py.
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, regenerate+compile+audit, preview screenshots.

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh "-fast -samples 3 -filter -bounce 2 -bouncegrid"

Preview the models before placing them: `python3 ../preview/md3sheet.py sheet.png --vfs <out> m1.md3 m2.md3 ...`.

Lessons (see also ../CLAUDE.md):
- Two overlapping rounded boxes (or two copies of a part at the same spot) give q3map2 "Duplicate or Flipped triangle"
  warnings and z-fighting; ribbons built as r 1 rounded boxes produced hundreds of them (use sharp boxes for thin parts).
- A misc_model with no collision still needs the audit's support rule: wall-mounted (wreaths, frames) and
  ceiling-hung (stars on threads) models count as supported when they touch the wall / ceiling brush.
- The tree MD3 casts shadows: the cave under its boughs needed its own lights.
- bspc leaves a groundless strip where a ramp meets a separate roof slab at the same pitch, so bots can't walk up; give
  them a pad and keep the ramp for players (`../pad_check.py` flies every pad, `../aas_check.py` finds the strip).
- Food on plate *models* floats (models have no collision): use a thin brush plate (`plate()`).
- A rug, tree skirt or track is a brush: anything standing on it starts at its top (`fz()`), or the audit reports overlaps.
- autosprite2 needs thin quads taller than wide (fire/candle flames: 2u slabs, nodraw on the other faces).
