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
- `xmas_textures.py` - every texture (original art), `padxmas.shader`, `wop_padxmas.arena` (shares helpers with playroom).
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, regenerate+compile+audit, preview screenshots.

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh "-fast -samples 3 -filter -bounce 2 -bouncegrid"

Lessons (see also ../CLAUDE.md):
- bspc leaves a groundless strip where a ramp meets a separate roof slab at the same pitch, so bots can't walk up; give
  them a pad and keep the ramp for players (`../pad_check.py` flies every pad, `../aas_check.py` finds the strip).
- Food on plate *models* floats (models have no collision): use a thin brush plate (`plate()`).
- A rug, tree skirt or track is a brush: anything standing on it starts at its top (`fz()`), or the audit reports overlaps.
- autosprite2 needs thin quads taller than wide (fire/candle flames: 2u slabs, nodraw on the other faces).
