# PadHamster (wop_padhamster)

Generator: `wopbuild.py padhamster gen` (or `OUT=<dir> python3 build_padhamster.py`). Quick look: `wopbuild.py padhamster preview`.
Full pipeline (after the layout is approved): `wopbuild.py padhamster check`, then `bots render levelshots package`.
Files: `hm_layout.py` (all coordinates), `hm_models.py` (textures + custom MD3/IQM), `build_padhamster.py` (layout).

## Design sheet
- Theme + scale: a sunny pet shop by day at Padman scale (~8u/cm, catalog models at 1.0).
- Playable area: one room 4096 x 3584 x 2048 (x -2048..2048, y -1792..1792, z 0..2048; north = +y). One structural
  hull (floor, walls, ceiling, sealed sky box behind the south shop window); everything else is detail / MD3 + weapclip.
- Centrepiece: the cage wall (north): a pine shelf unit (MD3 + matching weapclip) with three stacked hamster cages and the
  bottle shelf on top. Every cage board has a 160u open ledge in front of the cage; cage wire = alpha MD3 + `common/clip`
  (blocks players, not shots), tray rims = weapclip, two open doors per cage (door panels lie flat on the ledge).
  - Burrow cage (480): shavings floor, half-buried cardboard crawl tube (48u, `K.crawl`, Boaster inside), food hopper,
    hay nest walling off the dark west-back corner (the secret entry), bowls, nuts, toilet roll.
  - Wheel cage (960): spinning hamster wheel (`func_rotating` model2, axis y, clip column round it so nobody walks into it,
    mechanics sound), walk-in hide-house (Pad shield) with 16u chew-block stairs onto its flat roof.
  - Penthouse cage (1440): hammock on a stand, chew blocks, toilet rolls, Betty.
  - Bottle shelf (1760): three giant drinking bottles, Imperius behind the middle one, books, duck.
- Zones (each enterable AND climbable):
  1. Cage wall (above).
  2. Shop counter NE (top 560): walk-in compartments under it from the back aisle, till with an open walk-in cash drawer
     (8u floor, 16u rim), treat jar, shop screen. Mid shelf (1160) on the north wall over the back aisle.
  3. Cat tree (centre): carpet base, enterable cubby (roof = platform 400), platforms 800 (NE) and 1200 (over the cubby),
     sisal posts. An exercise ball (IQM, weapclip box) rolls a 760u loop round it on one `func_rotating`.
  4. Bird cage tower SE: walk-in cabinet (door west, shelf inside), round bird cage on top (door west, swinging perch +
     bird on a `func_pendulum`, Pumper inside), flat walkable roof at 1500 (Floater).
  5. Pet carrier SW: walk-in (east door, grille door open), flat roof 520 by pad, Bubble G inside. Round pet bed beside
     it (16u cushion, rim dips at the front) with a turning mobile overhead (IQM).
  6. Feed corner W: seed-sack 16u stairs (solid_piece MD3 = the step brushes) up to a sack landing at the burrow ledge;
     walk-in open-top feed bin.
  7. Window sill S (760): display baskets, bonsai, Speedy.
- Routes: main climb sacks -> burrow ledge -> lift A (glass tube, pad through a hole + collar) -> wheel cage -> lift B ->
  penthouse. Express: floor pad -> counter -> glass suction pipe (pad, tube follows the flight) -> mid shelf -> second pipe ->
  bottle shelf. Down: slick glass slide (39 deg, `K.slide`) from the penthouse deck down the west wall; pad bottle shelf ->
  cat tree P2 (bot exit from 1760). Cross-room pads: floor -> cat tree P1 / P2, P2 -> P3, P3 -> wheel ledge, floor -> burrow
  ledge, floor -> cabinet, cabinet -> bird cage roof, floor -> carrier roof, floor -> sill.
- Loot ladder: Imperius bottle shelf; Betty penthouse; Balloony cat tree top; Pumper bird cage; Splasher counter by the till;
  Boaster crawl tube; Bubble G carrier. Pad shield hide-house, Speedy sill, Floater bird cage roof, 2 shards. 4 ammo spots
  per weapon (two on open floor, two tucked away: under the shelf, cash drawer, cabinet shelf, under the counter, feed bin,
  behind the sacks), 3 Nipper ammo. 2 health stations (counter, pet bed). 16 spawns over floor, ledges and counter.
- Water: none.
- Secret: walk into the dark corner behind the burrow nest -> sealed Nest Vault under the world (Pad Power, Revival, Killer
  Ducks, Pad shield) -> teleporter back onto the pet bed; secret_found trigger beside the entry.
- Sightline blockers: cat tree in the middle, food box stacks, can pyramids, A-board sign, plush hamster, catalog duck,
  tire, plants, cardboard standup. Not measured yet (sight runs in the full build).
- Sounds: wheel mechanics (loop), clock ticking at the till, blackbird at the bird cage, kitten meow, distant dog bark,
  door chime (dingdong) on timers, secret_found.
- Arena: ffa lps team ft (no CTL: the room is not symmetric).

## woplib additions made for this map
- `K.slide()` (promoted from the four per-map `slide_brushes` copies), `K.tube_lift()` (pad inside a glass tube, vertical or
  along the flight), `K.cage_box()` / `K.cage_round()` (wire cages: alpha wire MD3 + clip, weapclip rims, open doors),
  `models.glass_tube()`. lint `rotors` understands annular sweeps (a ring round a static centre). bsp2scene: model2 and BSP
  surfaces sharing a shader no longer crash the page (and model2-only groups draw all their triangles).

## Checks
Quick preview stage only (see the build report); full build not run yet.
