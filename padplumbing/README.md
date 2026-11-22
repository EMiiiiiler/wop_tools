# Padman's Plumbing (wop_padplumbing) - design sheet

Generator: `wopbuild.py padplumbing gen` (or `OUT=<dir> python3 build_padplumbing.py`), models in `plumb_models.py`.

**Theme + scale:** a cut-away house about 6u per cm. The bathroom is upstairs, the crawlspace sits under its floor,
and the sewer culvert runs alongside. Pipes join everything.
**Playable:** x -2048..2048, y -1792..1792, z -192 (canal bed) .. 2000. Game types: ffa lps team ft syc_ffa.

## Zones
| zone | where | enter / climb |
|---|---|---|
| Bathroom | y 224..1792, floor 512. The open south edge is a balcony over the sewer hall | basement stairs, drain lift, express pipe |
| Bath | rim 842, water 270 deep | duck pad onto the caddy board; steps inside the bath lead out of the water |
| Toilet | seat 764, cistern 1004 | loo-roll pad onto the cistern; walking into the bowl flushes you into the drain tunnel |
| Vanity + mirror cabinet | counter 1022, cabinet top 1592 | open doors (walk in under the sink); soap pad to the counter, sponge pad to the cabinet top |
| Crawlspace | y 256..1792, floor 0, joists at 432 | three arches from the sewer hall, the missing-tile drop, the flush |
| Drain tunnel | x -1500..200, walkway 56 | ramps at both ends |
| Valve chamber | x 1632..2048, y 1432..1792 | shoot the red valve wheel to open the sluice gate for 12 s |
| Sewer hall | y -1792..224, full height | canal with an eastward current, plank + pipe bridges, steps out at both ends and in the middle |
| Water heater | top 960 | pressure-valve pad |
| Secret | bath plughole (underwater) | leads to the Lost & Found room (Pad Power, Revival, Killer Ducks, Padshield) |

## Loot ladder
Imperius on the mirror cabinet (two pads), Betty at the bottom of the sink, Splasher at the bottom of the bath,
Balloony on the water heater, Pumper in the drain tunnel, Boaster and Bubble G in busy spots. Each weapon has 3-4 ammo
spots: some are hidden (inside the vanity, the valve chamber, the canal bed), others sit in plain sight.

## Pads (themed, no discs)
Rubber duck, loo roll, soap bar, sponge and pressure valve, plus two pads inside glass pipes: the drain lift (crawlspace
to bathroom) and the express pipe (sewer floor, over the canal, onto the balcony).

## Sounds
Dripping taps, canal flow and bubbling, extractor fan, pump, water heater hum, toilet flush (one on the flush and a
distant one on a timer).
