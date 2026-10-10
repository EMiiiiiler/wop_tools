# Crater Crust / Crater Crust Deluxe

Generators for two World of Padman maps (night-time space pizza arcade, 1:4 human scale: 1 m = 128u).

- `build_map.py` - **wop_cratercrust** v2 layout (kitchen, storeroom, dining, arcade, parking lot, roof).
- `build_deluxe.py` - **wop_cratercrust_deluxe**: reuses the v2 layout through checked text edits, then adds
  the saucer + tractor-beam lift, photo-booth secret teleporter, tube slide, rocket carousel, bobbing claw,
  stage with applause trigger, aquarium, planet mobile, kitchen conveyor, walk-in freezer, rooftop greenhouse,
  rotating roof sign, ambient sounds and a cloud layer. Shapes beyond boxes come from `../wopmap.py`
  (`hull`, `cyl`, `sign_box`) via `mapgen_lib.from_wop`.
- `mapgen_lib.py` - box/plane brush library with SAT overlap tests used by the checkers.
- `check_and_write.py` / `check_deluxe.py` - run the layout, validate it and write the .map:
  brush overlaps, model support over the whole footprint, items/spawns not in solids or floating,
  jump-pad flights simulated with WoP physics (gravity 800; landing spot + clearance), ammo 3-6 per weapon.
- `gen_textures.py`, `gen_shader.py`, `gen_deluxe_textures.py` - all textures (original art) and shaders.
- `bsp_render.py` (software BSP renderer, top-down plans) and `guide.py` / `guide_deluxe.py` (annotated guide).
- `preview_night.css` - palette for `../preview/bsp2scene.py --style`.

    OUT=out ./build.sh            # both maps (or: ./build.sh v2 | ./build.sh deluxe)

Then compile as in the top-level README (BSP -meta -custinfoparms, VIS, LIGHT, bspc after light) and run
`../audit_map.py map --md3root <wop> --shaders out`, `../aas_check.py`, `../sightlines.py --bounds=-1824,-1056,2656,1056`.

Lessons from these maps are in the project notes: lights at z 600 under a 768u ceiling need ~1250-2400
each; aim jump pads at t_up/(t_up+t_down) of the way to the landing spot; give bspc ~20u clearance;
rotating parts need a common/origin brush, and nothing static may sit inside their sweep.
