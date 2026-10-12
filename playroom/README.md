# Padman's Playroom (wop_padplayroom)

A kid's bedroom at Padman scale (about 8u per cm, so catalog models sit at their native scale 1.0).
Room x -1792..1792, y -1536..1536, ceiling 1600; 12 portals, VIS instant, full bounce light ~95 s on 2 cores.

- `build_playroom.py` - the map: bed (jump pad up) + under-bed stash, nightstand, jump pad up to the desk,
  office chair, shelf cabinet + hutch (pad chain to the top shelf), dresser + aquarium (jump pad in, teleporter out,
  swimming fish on func_pendulum), window sill with a sunbeam and dust motes, ruler bridge, walk-in wardrobe, dollhouse
  (2 floors + roof deck, stairs inside), TV bench, rug playmat, brick ziggurat, ABC blocks, chess, toy box with lid ramp,
  loop-the-loop, toy rocket, play tunnel, book tent, toy train, garments on hangers, RC car (func_train + model2), rotating ceiling mobile, posters, mouse hole -> Pad's Hideout.
- `textures.py` - every texture (original art), `playroom.shader`, `wop_padplayroom.arena`. Sky is WoP's `env/fort-pad512`.
- `routes.txt` - on-foot routes for `aas_check.py --route`.
- `compile.sh`, `check.sh`, `render.sh` - dev compile, full regenerate+compile+audit, preview screenshots.

    OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh "-fast -samples 3 -filter -bounce 2 -bouncegrid"

Helpers worth reusing: `jumppad(x, y, z, land, apex, name)` aims from the trigger centre exactly like Q3's AimAtTarget
(target = apex), `mdl_c()` places a model by its bounding-box centre (for off-centre origins), `fit_top()` fits a
texture onto a top face (rugs, chess boards), `drawer_box()` builds a cabinet with fitted drawer fronts.

`pillow_md3.py` writes `models/mapobjects/playroom/pillow.md3` + `pillow.jpg` (curved pillow, 284 x 216 x 61).
The bed uses it by default (`PILLOW=brush` brings back the brush pillows) (a weapclip dome gives it collision).
