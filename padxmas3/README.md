# Padman's Christmas: Under the Tree (wop_padxmas3)

Generator: `wopbuild.py padxmas3 gen` (or `OUT=<dir> python3 build_padxmas3.py`). Full pipeline: `wopbuild.py padxmas3 all`.

## Design sheet
- Theme + scale: padxmas re-imagined from UNDER the tree. ~16u per cm (Padman 3.5 cm tall): presents are buildings,
  catalog toys at 1.4-2.5. Boughs overhead are the sky; the cream room wall closes the north; the rest of the living room
  is a custom blurred skybox (fireplace glow W, frosty night window S, lamp E, bokeh fairy lights) beyond invisible clip.
- Playable area: 5120 x 4608 (x -2560..2560, y -2304..2304), floor 0 = wine carpet, felt tree skirt with fur hem.
- Centrepiece: green plastic tree stand (832u square, rim 320) full of water, trunk through the middle, 4 chrome clamp
  screws as bridges from the rim to the trunk, sloped feet E/W as ramps, 16u steps out of the water; the canopy (4 whorls
  of needle-card boughs, baubles, fairy-light swags) and one walkable lowest branch (1104 -> 984).
- Zones: present tower NE (box A 768x640x576 walk-in through a torn corner, box B on top, slinky/bow pads), gingerbread
  house SW (door, windows, flat iced roof, chocolate 16u stairs + gumdrop pad), fallen broken bauble SE (walk inside),
  empty wrapping-paper tube W (tunnel; unrolled sheet = ramp to its top), toy train S (walk-in cab, roof via bow pad) +
  present tunnel over the track (roof via ribbon-spool pad), milk & cookies for Santa NW (plate, cookie stacks, letter).
- Pads (all theme objects, no discs): tambourine (floor -> branch root), slinky x2 (floor -> box A lid, inside A up
  through the lid hatch), red bow (A -> B), gold bow (B -> branch tip), gumdrop x2 (ginger roof, tube top), silver bow
  (cab roof), ribbon spool (tunnel roof).
- Loot ladder: Imperius branch tip | Betty box B lid | Balloony ginger roof | Pumper bottom of the stand's water |
  Splasher inside the bauble | Boaster inside the tube | Bubble G on the cookie plate. 4-5 ammo spots each.
- Water: the stand bowl (112 deep), 16u steps on the south inside wall; the screws are bridges just above it.
- Secret: drain grate on the bowl floor (under water) -> inside a gold present (Pad Power, Revival, Killer Ducks),
  teleporter back to the cookies.
- Sightline cover: small presents, ABC blocks, pinecones, candy canes, lying baubles, gingerbread men, gummy bears.
- Sounds: water_rippling (stand), electric_sizzle (socket), clock_ticking, wind_chimes, kitten_meow, snoring (secret).

## Checks
(wopbuild writes report.md in the build folder; paste the summary here when the map ships)
