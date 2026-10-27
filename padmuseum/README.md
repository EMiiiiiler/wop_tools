# Midnight Museum (wop_padmuseum)

An FFA map in a natural history museum after closing time, at human scale (64u per metre). x east, y north, ground
floor z 0. Nine rooms on a 3 x 3 grid (4608 x 4096) round a great hall with a glass roof, a roof terrace over everything,
and the portico and forecourt to the south. WoP's night-city sky (env/pc-friday-13th-512), a moon through the skylight.

Everything but the sky hull is detail: 0 portals, BSP + vis ~35 s, full light (bounce 2) ~9 min.

- `build_museum.py` - the map:
  - **Great hall**: a mounted T. rex you can walk up from the tail tip to the skull (**Betty**), a humpback whale
    skeleton hanging on cables under the glass roof, an imperial stair (two flights rising from the side walls to a
    central landing, open underneath) up to the mezzanine ring, display cases, info panels, columns. Doors at
    mezzanine level open onto balconies over Egypt, the planetarium and the Ice Age hall.
  - **Ancient Egypt** (west): a step pyramid with a stair up the east face (**Pumper** on top) and a tunnel into the
    tomb (BamBam). Seated colossi, Anubis, obelisks, lotus columns, mummy cases, a gilded coffin.
  - **SECRET**: walk into the open, glowing sarcophagus in the tomb -> **the pharaoh's treasury**, sealed under the
    world: gold, a death mask, Pad Power, Revival, Killer Ducks, Imperius and Balloony ammo; a teleporter back.
  - **Planetarium** (east): the copper dome rises through the roof (starfield inside), star projector, two seat
    rings, an orrery turning in the dome (func_rotating IQM). A pad on the roof throws you onto the dome's lantern
    platform (**Imperius**), a fling pad takes you back down to the roof.
  - **Ice Age** (north): a woolly mammoth (pad onto its back, **Boaster**), moa skeletons, a sabre-tooth on a rock,
    Haast's eagle hanging from the ceiling, snowy rock dioramas.
  - **Gems** (south-west): a walk-in geode lined with glowing amethyst (**Splasher** inside), a pad onto its top
    and a fling pad off it; crystal clusters and cases.
  - **Deep ocean** (south-east): a giant squid in a glass tank (pad onto the tank, **Balloony**), sharks overhead,
    coral cases.
  - **Foyer** (south): ticket desk, a statue on a round plinth, the gift shop (**Bubble G**, plush dinosaurs, gummy
    bears), the front doors.
  - **Stair towers**: the night guard's security office (NW: CCTV desk, lockers, snoring) and the staff room (NE);
    each has a two-flight stair up to the roof terrace.
  - **Roof terrace**: plant units, a water tank, a dish, a telescope, the dome; a pad up onto the great hall's
    walkable glass roof. A pad in the forecourt goes up onto the portico roof.
- `mu_models.py` - every custom MD3/IQM (procedural meshes and textures): T. rex, whale, mammoth, moa, sabre-tooth,
  eagle, rock dioramas, pharaoh colossus, Anubis, obelisk, coffins, canopic jars, lotus column, mummy case, pyramid
  capstone, treasure, death mask, dome, projector, seat rings, orrery, meteorite, geode, crystal clusters, display
  cases, squid tank, sharks, coral case, classical columns, ticket desk, stanchions, benches, gift shelves, security
  desk, lockers, plant units, water tank, dish, lion, info panels, exit signs, CCTV, skylight frame.
- `mu_textures.py` - brush textures (marble, limestone, hieroglyphs, starfield, coffers, gem wall...),
  `padmuseum.shader`, `wop_padmuseum.arena`.
- `layout.py` - shared constants (rooms, doors, stairs, pyramid, dome/geode profiles); `mulib.py` - shader registry.
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padmuseum_source.zip` into a folder the game sees (for example `wop/zz_padmuseum.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padmuseum.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padmuseum.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padmuseum.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padmuseum.bsp

## Lessons
- bspc predicts a jump pad landing where the arc first touches ground, which on a small platform is the near edge.
  With the fling pad there (dome top, geode top) the landing area was the fling pad's own area and the pickup next to
  it was unreachable; putting the fling pad on the far side (and making the dome's platform r 160) fixed both.
- A pad onto a tall object under a low ceiling (squid tank, 120u headroom) is limited by the apex: pad_check passed
  at 116u margin but bspc's own flight hit the tank edge. Start the pad further away (the arc rises before it crosses
  the edge) and keep the apex under ceiling - 40.
- Long outer walls that span several rooms take one wall texture from their face centre: split walls per room when
  each room has its own wallpaper.
- Doorways aligned on one axis through four rooms gave 8.4 % long sightlines; a statue on a round plinth in the foyer,
  free-standing exhibit panels in the hall and a rock diorama in the Ice Age hall brought it to 3.8 %.
