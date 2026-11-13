# Pad Deep Dive (wop_paddive)

Generator: `wopbuild.py paddive gen` (or `OUT=<dir> python3 build_paddive.py`). Full pipeline: `wopbuild.py paddive all`.

## Design sheet
- Theme + scale: sunset dive centre from a reference photo (glass drum under a wave shell roof, cascade pools, causeway
  over a deep moat). Human scale ~48u/m, catalog models 0.3-0.9.
- Playable area: 4096 x 3776, east/west mirrored. Files: `pd_shape.py` (shared constants: roof wave, drum faces, lobes),
  `pd_models.py` (MD3s), `build_paddive.py` (layout).
- Centrepiece: the Shell (drum r 600, roof crest z 736): lobby z 0, gallery ring z 256, roof walkable (32u clip strips
  following the wave under the MD3 skin). 640u dive shaft in the lobby, diving board from the gallery.
- Zones: plaza (south), causeway + two moats (-280), cascade terraces d/c/b/a (64/128/192/256) each side joined by 16u
  stairs, top terraces -> gallery doors, back garden, lawns with palms.
- Loot: Imperius roof crest (pads from the top terraces, bubble teleporter at the shaft bottom), Betty shaft bottom,
  Balloony gallery, Pumper east top terrace, Splasher west moat floor, Boaster west cascade, Bubble G plaza.
- Water exits: 16u steps to a 24-40u shelf (south end of each moat, south side of the shaft). Terraces carry an 8u sheet.
- Secret: swim in behind the big waterfall (niche under terrace b, both sides) -> sealed vault at z -1200.
- State: quick preview published for layout review; full check/bots/final build still to do.
