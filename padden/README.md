# Respawn Room (wop_padden)

Generator: `wopbuild.py padden gen` (or `OUT=<dir> python3 build_padden.py`). Full pipeline: `wopbuild.py padden all`.

## Design sheet
- Theme + scale: a teenage gamer's bedroom at night, Padman scale ~8u/cm (catalog models at 1.0). Room 4096 x 3584 x 2048, night city through the south window (env/pc-friday-13th-512), RGB LED strips.
- Centrepieces (custom MD3, dn_models.py): loft bed with a den under it, wardrobe (walk in through the open door), chest of drawers, RGB gaming desk + triple monitors + keyboard/headset, walk-in PC tower with spinning fans (func_rotating IQMs), gaming chair, CRT + retro console, bean bags, mini fridge, pizza-box staircase, drinks cases, laundry, backpack, guitar, skateboard, bin, speakers, radiator, curtains.
- Levels: floor 0 | tower top 456 | desk 600 (monitor-box ramp) | dresser 720 | sill 760 | loft bed 1216 | desk shelf 1280 | wardrobe top 1760. Every high level drops to a lower one < 1000u (bed -> dresser, wardrobe -> bed, shelf -> desk).
- Loot: Imperius wardrobe top (pad from the bed), Betty loft bed (2 floor pads), Balloony desk shelf (pad from the desk), Pumper desk, Splasher dresser, Boaster inside the PC tower, Bubble G by the bean bag. 3-4 ammo spots each.
- Secret: walk into the static on the CRT under the bed -> an 8-bit level under the world (Pad Power, Revival, Killer Ducks, Pad shield), teleporter back.
- Sounds: PC fan, TV static, clock, fridge hum, police siren and pizza door buzzer on timers, stream chatter, applause on the wardrobe top.

## Checks
(wopbuild writes report.md in the build folder; paste the summary here when the map ships)
