# Sandcastle Showdown (wop_padsandcastle)

Generator: `wopbuild.py padsandcastle gen` (or `OUT=<dir> python3 build_padsandcastle.py`). Full pipeline:
`wopbuild.py padsandcastle all`. Quick look: `wopbuild.py padsandcastle preview`.

## Design sheet
- Theme + scale: a Kiwi summer beach at Padman scale (~8u per cm, catalog models at 1.0). Two rival sandcastles
  built by kids, a sand mountain with a tunnel between them, the sea on the south side, dunes on the north.
- Game types: CTL first (mirror-symmetric in x: red west, blue east), plus FFA / LPS / team / FT / 1LC.
- Playable area: 5248 x 3584 (x -2624..2624, y -1792..1792). Sand at z 0, the beach slopes into the sea south of
  y -900 (sea floor -48, water -10: wading depth everywhere except the rock pool).
- Centrepieces (custom MD3): two bucket-moulded castles (ribbed keep with an arched door and arrow slits, four
  turrets, walls with crenellations, lolly-stick bridges and lintels, team flags), Mount Sandy (two-tier sand
  mountain with a tunnel), the giant beach umbrella, chilly bins with bodyboard ramps, spade, buckets, beach ball,
  crab, seagulls, shells, starfish, rocks, driftwood, dune grass.
- Landmark zones (each enterable and climbable):
  - **Castles** (x +-1400..2400, y -150..1050): drawbridge over the moat into the courtyard, keep with the team lolly
    inside, pad up through the keep roof hatch and a courtyard pad onto the keep roof, 16u sand stairs to the wall
    walk, turrets one step up from the walls, posterns north and south.
  - **Mount Sandy** (centre, 0,300): 16u stairs east and west onto the lower terrace, pads onto the summit, tunnel
    north-south through it with the neutral lolly (1LC) in the middle.
  - **Rock pool** (south centre): 16u sand steps down both ends, Splasher on the bottom, boulders round it.
  - **Picnic** (north): giant umbrella over a beach towel, chilly bins (bodyboard ramps) both sides.
  - **Shallows** (south): wade anywhere; beach slope is the exit everywhere.
- Loot ladder: Imperius on the summit; Balloony on each keep roof; Betty on each chilly bin; Pumper on the mountain
  terrace (mid-field, after padbath's lesson); Splasher at the bottom of the rock pool; Boaster in each courtyard;
  Bubble G by each drawbridge. 3-6 ammo spots per weapon, some on the wall walks and in the tunnel.
- Water + exits: moats (40 deep, sloped banks), sea (38 deep, beach slope), rock pool (198 deep, 16u steps both ends).
- Secret: walk into the mouth of the giant conch shell behind the umbrella -> the Mermaid's Grotto (sealed under the
  world: Pad Power, Revival, Killer Ducks, Pad shield) -> teleporter back beside the umbrella pole.
- Sightline cover: the mountain blocks the centre; beach ball, spade + bucket, crab, driftwood, seagulls, rocks
  in the south band; chilly bins, beach bag and the conch in the north band.
- Sounds: water rippling/flowing along the shore and the moats, wind chimes under the umbrella, applause on the
  summit, secret found.
