
## Build status (final)
compile 1 portal, aas 0 problems / all pads linked, lights median 67 (6.3 % dark), sight 4.8 % (WARN looked at:
carousel horses and open midway), bots: every weapon picked up, secret strongroom items taken.

## Lessons
- model2 is never scaled: big spinning rims must be saved as IQM (`K.ent` now refuses a scaled model2).
- Pickups on a faceted cone crown (big top) are unreachable for bspc; put them on a flat top (bleachers).
- `town.Building(ground_z=...)` for buildings on wheels/plinths, so the outside door route point is on the ground.
