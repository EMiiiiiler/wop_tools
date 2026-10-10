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

## Tools
- `check_entities.py <map>`: lists entities inside solid brushes.
- `padcounter/build_padcounter.py`: map generator and reusable brush helpers. `GL` env var scales all models (1.0 = native); `OUT` sets the output folder.

## Known pitfalls
- Models only appear in-game if q3map2 baked them in; a "failed loading model" error means the compile command's paths are wrong.
- Pickup classnames should be verified against WoP's entities.def.
- `Unknown surfaceparm: "woodsteps"` is harmless with `-game quake3`.
