# wop_tools

Tools and standing rules for building World of Padman (WoP) maps.

## Setup
- Editor/compiler: NetRadiant Custom (https://github.com/Garux/netradiant-custom/tree/20260114). Give answers in terms of it.
- No WoP gamepack is used. Compile with `-game quake3 -fs_basepath "<WoP install dir>/" -fs_game wop`, as separate tokens. Check the VFS lines at the top of the log list the wop pk3s, or every misc_model fails to load.
- The user often runs q3map2 under Wine (Z: paths), so file name case can matter.
- Bot pathing is built with bspc after `-light`, from the final BSP.

## Map rules
- Use models from https://worldofpadman.net/en/tutorials/catalog-map-objects/ to make maps feel full.
- Always produce a `.shader` and `.arena` file, and include any textures.
- Never place solids or entities inside another entity or solid. Run `check_entities.py` on every generated map.
- Keep portal counts low: make most brushes detail.
- All models must sit fully on a surface, not float or overhang empty space.
- Break up long sightlines with models.
- Put good weapons in hard-to-reach places (top shelf, bottom of the sink).
- Give each weapon 3-6 ammo spots, some hidden and some in plain sight.
- Any water needs a way out (portal, ladder or ramp). Note bots do not climb ladders; use stairs or jump pads.
- Full explorability: every door or building can be entered, and every building can be climbed. Rooftop access must not have geometry blocking line of fire to other players.

## Tools (see README.md)
- Generate with `wopmap.py`; place models with `md3bounds.json` so they rest on surfaces.
- Before delivering any map run: `audit_map.py` (must say RESULT: OK), `aas_check.py` after bspc (RESULT: OK),
  `sightlines.py` (aim for < ~4% of rays over 1800u), then look at it with `preview/bsp2scene.py` + `shoot.py`.
- If wopded is available, run the map with bots and read games.log for pickups/frags.
- `waterpark/` is the reference generator (zones, holes for pools, slides, facades, decoration).

## Known pitfalls
- Texture preview: Q3 texture t runs downward; three.js textures need flipY=false or signs look upside down.
- misc_model is static; animated models need `misc_externalmodel` (no modelscale) with animationStart/End/FPS.
- An item origin must sit 16u above the floor (bbox +-15) or the game drops it as "in solid".
- Probe AAS areas at floor+25 (standing origin); floor+24 sits exactly on the boundary.
- Models only appear in-game if q3map2 baked them in; a "failed loading model" error means the compile command's paths are wrong.
- Pickup classnames should be verified against WoP's entities.def.
- `Unknown surfaceparm: "woodsteps"` is harmless with `-game quake3`.
