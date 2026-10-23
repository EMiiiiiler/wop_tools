# Tlaloc's Lagoon (wop_padaztec)

An FFA water park built as an Aztec temple complex in a jungle clearing on a sunny day, human scale (~32u per metre,
Padman 56u). x east, y north, plaza z 0, water z -16. Playable area 4608 x 4096 inside jungle banks; a custom sky cube
(jungle hills, two snow-capped volcanoes to the north, one smoking) with a scrolling cloud layer; the sun stands in
the north (southern hemisphere).

Everything but the sky hull and the sealed secret room is detail: 0 portals, BSP + VIS ~20 s, fast light ~20 s,
full light (-bounce 2 -bouncegrid) see below.

- `build_aztec.py` - the map:
  - **Great Pyramid of Tlaloc** (centre north): four talud-tablero tiers with painted friezes (Tlaloc goggle masks,
    feathered serpent heads), every terrace walkable; steep 16u x 16u Aztec stairs up the south and north faces
    with feathered-serpent balustrade heads at their feet. On the summit **Tlaloc's shrine** (blue-and-white striped
    walls, a Tlaloc mask over the door, the rain god's idol inside, giant fire braziers) and a pad onto its roof
    (**Imperius**, applause when you land). A tunnel runs east-west through the base past the **tomb** (Chacmool
    altar, braziers, **Bubble G**).
  - **Serpent tube** (closed slide): walk into the open jaws of a feathered serpent on the summit; the scaled green
    tube with feather collars winds down the west side of the pyramid and drops you into the west lake.
  - **Eagle flume** (open slide): under an eagle-warrior head arch on the east side of the summit, down into the
    plunge pool.
  - **Lagoon** (south): an octagonal lake split by a red-stone causeway (Tenochtitlan style) into two lakes with a
    48u wading ring and a deep centre; the **Sun Stone** stands upright on the island, a **geyser pad** fires you
    from the island onto the summit. Rock islets with palms in both lakes (cover), 16u steps out of the water on
    four sides, a sand beach on the east lake. **Splasher** on the bottom of the west lake.
  - **Cenote** (north-west): a limestone sinkhole with vines; a stair spirals down the wall to the water (the last
    steps continue under water, so you walk out), a stone serpent spout pours a waterfall. **Pumper** on the bottom.
  - **SECRET**: deep under water on the cenote wall a golden serpent's jaws frame a tunnel -> **Moctezuma's
    treasure** (sealed under the world): gold heaps, a turquoise mask, a small Sun Stone, jaguars; Pad Power,
    Revival, Killer Ducks, Imperius + Betty ammo; a teleporter back to the plaza.
  - **Temple of the Jaguar** (west): talud-tablero platform, stair east between two stone jaguars, a walk-in shrine
    (idol, Pad shield) and a pad onto its roof (**Balloony**).
  - **Plunge pool** (east): the flume's splash pool, 16u steps out at the south end, **Floater** on the bottom,
    lifeguard tower.
  - **Tlaloc's head** (north-east): a giant stone head of the rain god (goggle eyes, fangs, curled lip, ear spools,
    feather headdress) pouring water from its mouth into a splash pool; a pad behind it onto the crown (**Betty**).
  - **Hall of the Eagle Warriors** (north): a colonnade of feathered-serpent columns (heads at the floor) with a
    painted back wall, a bench, a health station; a stair up to the roof (Jumper).
  - **Ball court** (south-east): a tlachtli alley with sloped red benches, carved walls, stone rings, the rubber
    ball; stairs up both outer walls (Pad shield on top), Speedy in the alley.
  - **Cantina** (south-west): walk-in snack bar with a turquoise mosaic counter, bottles, menu board, thatched
    awnings and bar stools (**Boaster** inside); a stair and a pad to the roof terrace with palapa parasols.
  - Plaza dressing: braziers with fire, palms, agaves, monstera, carved stelae, mossy boulders, fallen ruins,
    loungers, palapa parasols, inner-tube racks, lifeguard towers, rubber ducks, amphorae, skulls by the tunnel.
  - **Quetzalcoatl** (the feathered serpent, IQM on a func_rotating) circles the pyramid in the sky with an eagle's
    cry now and then; birds, cicadas, fire, falling water and dripping caves on target_speakers.
- `az_shapes.py` - the convex solids shared by the builder (invisible `common/weapclip` collision) and the models
  (visible surfaces): pyramid tiers + stairs (carved by the stair notches, tunnel and tomb), shrine, jaguar temple,
  ball court, eagle hall, cantina. `azlib.solids_mesh()` turns brush solids into lightmapped MD3 surfaces (hidden
  faces culled, per-face texture/UV callback), so the collision always matches the model.
- `az_models.py` - every custom MD3/IQM (procedural meshes and textures): pyramid, shrine, idol, Chacmool, braziers,
  serpent heads, serpent tube + head, eagle flume + head, Sun Stone, Tlaloc head, jaguar temple, jaguar statue, ball
  court + rings + ball, eagle hall, serpent columns, cantina, stools, palms, agaves, monstera, parasols, loungers,
  inner tubes, tube rack, lifeguard tower, stelae, boulders, ruins, vines, waterspout, secret mouth, gold heaps,
  turquoise mask, Quetzalcoatl.
- `az_textures.py` - brush textures (plaza flagstones, tezontle setts, step-fret friezes, carved glyph walls, painted
  stucco, turquoise mosaic, pool tile with caustics, cenote limestone, jungle bank, grass...), the jungle sky cube
  `env/padaztec/jungle_*`, `padaztec.shader`, `wop_padaztec.arena` (ffa lps team ft syc_ffa syc_tp).
- `layout.py` - shared constants (pyramid tiers/stairs, lagoon octagon, slide paths, cenote spiral...).
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padaztec_source.zip` into a folder the game sees (for example `wop/zz_padaztec.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padaztec.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padaztec.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padaztec.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padaztec.bsp

## Checks (Oct 2026)
audit_map OK, pad_check OK (5 pads), aas_check OK (every pickup reachable, 20 routes incl. both pyramid stairs, every
terrace, the shrine door, tube mouth, cenote stair, all building stairs), sightlines 3.0 % of rays over 1800u.
Bots (10, FFA 5 min): 69 kills, every weapon taken (Boaster 30, Imperius 24, Betty 15, Pumper 12, Bubble G 12,
Splasher 6, Balloony 3), the secret found (Pad Power 2).

## Lessons
- Brush solids -> MD3 (`azlib.solids_mesh`): big architecture keeps exact collision and still gets MD3 detail
  (cornices, mouldings, painted friezes fitted per tablero band). Use a low `q3map_shadeAngle` (20-30) on
  architecture shaders or talud/tablero edges get smoothed.
- A 45-degree Aztec stair (16 rise, 16 run) is fine for players and bots in the open; terraces connect to it where
  a step top is level with (or 16 above) the terrace beside the stair notch.
- `wopmap.carve()` could emit a zero-area sliver face (three collinear plane points, NaN normal) when cutting an
  octagon with cylinders; `brush_from_planes` now drops such faces.
- Bots ignored a Boaster in a walk-in tomb (0 pickups in 3 min) but took it 30 times in the cantina; the tomb's
  Bubble G then got 12: weapon weight vs. detour matters.
- An item on a rock islet 16u above the water is effectively unreachable (Q3 water jump) - islets are cover only.
