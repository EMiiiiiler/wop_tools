# Backyard BBQ (wop_padbbq)

An FFA map in a Kiwi backyard on a summer afternoon, at Padman scale: 5u per cm, so Padman is an 11 cm toy, the
kettle barbecue is a tower and the paddling pool is a lake. x east, y north, lawn z 0, yard 4608 x 4096 inside paling
fences, the weatherboard house along the north side (the sun is in the north and the house face is in its own shade).
WoP's sunny garden sky (env/fort-pad512), the neighbours' trees and cabbage trees beyond the fences.

Everything but the sky hull is detail: 0 portals, fast compile ~45 s.

- `build_bbq.py` - the map:
  - **Deck + pergola** (north-west, against the house): an outdoor table setting, planters (lemon tree, flax), a
    lattice skirt with three gaps to **crawl under the deck** (Bubble G, Boomies, Visionless, spiders). A pad from the
    deck onto the **pergola's slat roof** (Imperius) among the grapevine and festoon lights; a fling pad back down.
    The roof walk is player clip, so shots go through the gaps between the slats (items up there are suspended).
  - **Kettle barbecue** (centre): walk up a pile of charcoal briquettes (16u steps) into the ash catcher under the
    bowl (**Splasher**); a pad onto the cooking grate (**Betty** among the sausages, patties, corn and kebabs; the
    middle over the glowing coals burns, slowly). The lid hangs on its side hook; the chilly bin and the charcoal bag
    stand beside it.
  - **Paddling pool** (west): foam play-block steps up over the inflatable rim and down inside, **Pumper** on the
    bottom, a swim ring and a rubber duck drifting round (func_rotating IQM).
  - **Dad's shed** (south-west): walk in (mower, shelves with paint tins, tools, pot stack), a pad onto the
    workbench; a pad from the lawn onto the corrugated roof (**Balloony**).
  - **Kennel** (north-east): REX's kennel, walk in (**Boaster**), a pad onto the ridge (Speedy).
  - **Cubby house** (south-centre): the kids' playhouse, walk in (table and stools), a pad onto the ridge.
  - **Picnic table** under the striped parasol (south-east): lunch (plates, sauce bottles, cans), a pad onto the
    table (Pad shield).
  - **Sun lounger** (south): a beach towel hangs down as a ramp, Floater on the seat, walk up the backrest.
  - **Vege bed** (east fence): brick steps up into the tomatoes, lettuces and carrots (BamBam).
  - **Lawn**: a rotary clothesline turning in the breeze (washing on it), a sprinkler spinning (water jets), the hose
    from the reel, a toddler slide (walk up the chute), a clam-shell sandpit with its lid up, a round garden bed with a
    cabbage tree, a ride-on toy car, firewood stacks, wheelie bins, a compost bin, a bird bath, gnomes, backyard
    cricket stumps, toys, grass tufts.
  - **SECRET**: walk into the little door in the **ant hill** by the south fence (secret sound, ants marching round it)
    -> **the ant colony**, sealed under the world: earth pillars, the queen, larvae, a seed larder; Pad Power,
    Revival, Killer Ducks, Imperius ammo; a WoP teleporter back to the lawn.
- `bb_models.py` - every custom MD3/IQM (procedural meshes and textures): the kettle, briquette steps, pool, foam
  steps, pergola, deck trim, house trim (windows, gutter, downpipes, tap), heat pump, outdoor setting, planters,
  clothesline, shed trim, workbench, mower, shelves, garden tools, a `little_house()` generator (kennel, cubby house),
  picnic table + parasol, lounger + towel, vege plants, wheelbarrow, gnomes, sprinkler, hose reel + hose, ants,
  ant hill, queen, larvae, seed pile, colony pillars, cabbage trees, fence rails, slide, bins, log piles and more.
- `bb_textures.py` - brush textures (lawn with daisies, weatherboards, palings, decking, lattice, soil, sleepers,
  brick, corrugated iron...), `padbbq.shader`, `wop_padbbq.arena`.
- `layout.py` - shared constants (zones, roof profiles, stairs); `bblib.py` - shader registry.
- `routes.txt` - on-foot routes for `aas_check.py --route` (generated).
- `compile.sh`, `check.sh`, `render.sh`, `botrun.sh`, `package.sh`, `env.sh` (cloud session paths).

      OUT=out GAME=~/Games/wop Q3MAP2=q3map2 BSPC=wopbspc ./check.sh

## NetRadiant Custom (no WoP gamepack)
Unzip `wop_padbbq_source.zip` into a folder the game sees (for example `wop/zz_padbbq.pk3dir/`) and compile:

    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -meta -custinfoparms maps/wop_padbbq.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -vis -saveprt maps/wop_padbbq.map
    q3map2 -game quake3 -fs_basepath "<WoP dir>/" -fs_game wop -light -fast -samples 3 -filter -bounce 2 -bouncegrid -custinfoparms maps/wop_padbbq.map
    bspc -forcesidesvisible -optimize -bsp2aas maps/wop_padbbq.bsp

## Lessons
- An open lawn at Padman scale measured 14.9 % long sightlines with the landmarks alone. Big themed cover in the
  middle band brought it to 4.2 %: a walk-in cubby house, a clam-shell sandpit whose open lid stands up as a shield, a
  round bed with a cabbage tree, a ride-on car, a slide, firewood stacks, wheelie bins, a compost bin, a bird bath.
- Items drop at spawn with a MASK_SOLID trace: on a player-clip floor (the pergola slats) they fall through while bots
  still head for the original spot. Imperius had 0 pickups until it got `spawnflags 1` (suspended), then 24-47.
- A jump pad landing within the trigger_hurt radius + 15 lands in a bspc lava area and bots never take it: shrinking
  the barbecue's hot zone and moving the landing out took Betty from 0 to 22 pickups.
- `little_house(spec)` builds a gabled house's collision (walls with openings, two slope slabs, a ridge walk 4u proud)
  and its MD3 (boards, arched door, window trims, shingle grids, ridge cap) from one spec in layout.py.
