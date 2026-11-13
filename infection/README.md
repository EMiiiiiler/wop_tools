# Infection for World of Padman

A Halo-style Infection mode. It is a server-side mod: only the game logic (`qagame.qvm`) changes, so the stock WoP
client, menus, HUD, maps and bots keep working and friends who join your server need nothing extra.

## Rules
- Two teams: **survivors** (Blue Noses) and **infected** (Red Pads).
- Each round one or two players are picked as infected. They do not spawn: they wait as free-flying spectators and see
  a countdown.
- Everybody else spawns as a survivor and has `g_inf_prepTime` seconds (default 120) to collect weapons and find a
  place to defend.
- Then the infected are released. They only have the Punchy: one punch kills an unarmoured survivor. They cannot pick
  up weapons, ammo or holdables (power-ups and armour are allowed), run a little faster and start with armour.
- A survivor who dies, however it happens, respawns as infected.
- The round ends when everyone is infected (infected win) or after `g_inf_roundTime` seconds (default 300; the
  survivors win and each one alive gets bonus points). A new round starts 6 seconds later with new infected.
- The team scores count rounds won; `pointlimit` is the number of rounds to win the map.
- Bots work: infected bots hunt the survivor they can reach fastest.

## Install and play
1. Copy the `infection` folder next to the `wop` folder of your World of Padman install (so you have
   `<WoP>/wop` and `<WoP>/infection/zz_infection.pk3`).
2. Start WoP with `+set fs_game infection +exec infection.cfg +map <mapname>`, e.g.
   `wop.x86_64 +set fs_game infection +exec infection.cfg +map wop_padgarage`.
   Your own maps in `wop/` are found as usual.
3. Join with the normal team menu (any choice works; the mode assigns the team).

`infection.cfg` holds every setting with a comment. `g_infection 0` turns the mode off (plain WoP).

| cvar | default | meaning |
|---|---|---|
| `g_infection` | 0 (1 in the cfg) | on/off, needs `g_gametype 6`; latched until the next map load |
| `g_inf_prepTime` | 120 | seconds before the infected are released |
| `g_inf_roundTime` | 300 | seconds the survivors must hold out (0 = no limit) |
| `g_inf_startInfected` | 0 | infected at round start (0 = 1, or 2 with six or more players) |
| `g_inf_meleeDamage` | 100 | damage of an infected punch |
| `g_inf_meleeRange` | 64 | reach of an infected punch (normal 32) |
| `g_inf_infectedSpeed` | 1.15 | speed factor of the infected (on top of the Punchy's 1.3) |
| `g_inf_infectedArmor` | 100 | armour the infected spawn with |
| `g_inf_surviveBonus` | 5 | points per survivor alive at the end |

## Build from source
`./build_mod.sh <WoP source checkout>` applies `src/infection.patch` + `src/g_infection.c` (made against the commit in
`src/WOP_COMMIT`), builds `qagame.qvm` with the repo's own q3lcc/q3asm and writes `dist/infection/` and
`dist/wop_infection_mod.zip`. `test_mod.sh <WoP source checkout>` runs a short bot match on the dedicated server and
checks the round flow in `games.log`.

The game code is GPL-2.0 like WoP's; the patch and the new file are inside the pk3 (`src/`).

## How it is wired (for later changes)
- `g_infection.c`: round state machine (IDLE, PREP, HUNT, END), a role per client (survivor, waiting, infected) and
  `INF_SyncRoles()` which keeps teams equal to roles every frame.
- Hooks: `G_RunFrame` (round logic), `player_die` (infect), `G_Respawn` (team switch before the spawn), `SetTeam` (team
  requests), `ClientSpawn` (loadout), `Touch_Item` (pickups), `CheckGauntletAttack` (damage, reach), `ClientThink`
  (speed), `AddScore` (team score = rounds), `CheckTournament` (no warm-up), `G_CheckMinimumPlayers` (bots as one pool).
- Bots: `BotInfectionHuntGoal` in `ai_dmnet.c`; `BotChooseWeapon` falls back to the Punchy when the weapon weights
  return nothing (stock code left weapon 0 selected: "weapon number (0) out of range").

## Not checked
Only the dedicated server with bots was tested here (no graphical client): the centre-screen messages, sounds and the
view of a waiting infected have not been seen on a real client.
