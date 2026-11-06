# Neon Tide (wop_padwave)

Generator: `wopbuild.py padwave gen` (or `OUT=<dir> python3 build_padwave.py`). Full pipeline: `wopbuild.py padwave all`.

## Design sheet (fill in BEFORE building - see SKILL.md section 1)
- Theme + scale: (e.g. Padman scale ~8u/cm, catalog models at 1.0)
- Playable area: 2304 x 4608 (good maps are 4000-5000 x 3000-4500; aisles 128-224u)
- Centrepiece (custom MD3):
- 4-8 landmark zones (each enterable AND climbable, roof access by 16u stairs or a pad):
- Routes between zones (every route goes in routes via K.route / stairs16(route=)):
- Loot ladder (hardest spot -> best weapon; Imperius 1600 > Betty/Balloony 1200 > Pumper 1000 > Splasher 900 >
  Boaster 800 > Bubble G 400), 3-6 ammo spots per weapon:
- Water + its exits (16u steps into <= 44u deep water):
- Secret (non-obvious entry -> sealed room: Pad Power, Revival, Killer Ducks; teleporter back):
- Sightline blockers in the open middle band:
- Sounds (sound/world/... that exist):

## Checks
(wopbuild writes report.md in the build folder; paste the summary here when the map ships)
