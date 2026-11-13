# Infection for World of Padman

A Halo-style Infection mode. The mode itself is server-side (`qagame.qvm`), so the stock WoP HUD, maps and bots keep
working and friends who join your server need nothing extra. A patched menu (`ui.qvm`) adds it to Create Game.

## Rules
- Two teams: **survivors** (Blue Noses) and **infected** (Red Pads).
- Each round one or two players are picked as infected. They do not spawn: they wait as free-flying spectators and see
  a countdown.
- Everybody else spawns as a survivor and has `g_inf_prepTime` seconds (default 120) to collect weapons and find a
  place to defend.
- Then the infected are released. They only have the Punchy: one punch kills an unarmoured survivor. They cannot pick
  up weapons, ammo or holdables (power-ups and armour are allowed).
- A survivor who dies, however it happens, respawns as infected.
- **First infected are strong, converts are weak.** The infected a round starts with run faster, reach further and
  have armour; survivors who get infected only get a slightly longer reach. Rounds build up to a last stand.
- The round ends when everyone is infected (infected win) or after `g_inf_roundTime` seconds (default 300; the
  survivors win and each one alive gets bonus points). A new round starts 6 seconds later.
- The team scores count rounds won; `pointlimit` is the number of rounds to win the map.

## Playing with bots
- **Your role**: `g_inf_humanRole` 0 = random, 1 = you always start as a survivor, 2 = you always start infected.
  When every human starts infected the preparation is cut to `g_inf_infectedPrepTime` (30 s).
- **Survivor bots defend.** `g_inf_botHoldLead` (30) seconds before the release they stop collecting. Two of them
  (`g_inf_botEscort`) come and find you, and every other survivor bot that sees you joins (`g_inf_botJoinOnSight`):
  they stand in a loose ring round you, follow when you move, watch for the infected and do not chase them. Bots that
  never see you hold the map's best spots in groups of three (health stations, armour, power-ups, weapons; high ground
  preferred).
- **Hiding works.** Infected bots only know where a survivor fired a weapon, was seen by one of them, or was "pinged"
  (every `g_inf_pingInterval` = 15 s all survivors are revealed once). A bot that reaches the place and finds nobody
  forgets it and searches on. `g_inf_botAwareness 0` gives them back perfect knowledge.
- **Difficulty follows you** (`g_inf_adaptive 1`): one level up after a round you win (you survive, or as infected you
  get everyone), one down after a round you lose, from -4 to 6, kept in `g_inf_level` between sessions. As a survivor
  each level gives the infected 3 % speed and 15 armour, and every second level one more infected at the start. When
  you play infected it works the other way round: higher levels give the survivors 20 armour each, lower levels
  strengthen your side.

## Install and play
1. Copy the `infection` folder next to the `wop` folder of your World of Padman install (so you have
   `<WoP>/wop` and `<WoP>/infection/zz_infection.pk3`).
2. Start WoP, open **Mods** in the main menu and pick **Infection** (or start WoP with `+set fs_game infection`).
3. **Create Game**: the game type list has a new last entry, **Infection**. With it selected the options show
   **Your Role** (Random / Survivor / Infected) and **Prep Time** in place of Friendly Fire and Start Lives. Point Limit
   is the number of rounds to win. Every map made for Free For All or team play is listed. Pick bots with Select Bots,
   or pick none and the game fills up to 8 players by itself. Press Fight.
4. In the game join with the normal team menu if asked (any choice works; the mode assigns the team).

Without the menu: `wop.x86_64 +set fs_game infection +exec infection.cfg +map <mapname>`.

The menu entry is a patched `ui.qvm` inside the same pk3, so it only exists while the Infection mod is loaded; plain
WoP is untouched. Any map with bot support works, nothing to rebuild.

`infection_settings.cfg` holds the fine tuning with a comment per line and is loaded automatically (`autoexec.cfg`);
`infection.cfg` is for starting from the command line. Other game types still work inside the mod.

| cvar | default | meaning |
|---|---|---|
| `g_infection` | 0 (1 in the cfg) | on/off, needs `g_gametype 6`; latched until the next map load |
| `g_inf_prepTime` | 120 | seconds before the infected are released |
| `g_inf_roundTime` | 300 | seconds the survivors must hold out (0 = no limit) |
| `g_inf_startInfected` | 0 | infected at round start (0 = 1, or 2 with six or more players) |
| `g_inf_humanRole` | 0 | 0 random, 1 humans always survivors, 2 humans always infected |
| `g_inf_infectedPrepTime` | 30 | preparation when every human starts infected (-1 = full time) |
| `g_inf_meleeDamage` | 100 | damage of an infected punch |
| `g_inf_meleeRange` / `g_inf_convertedRange` | 64 / 48 | punch reach of first infected / converts (normal 32) |
| `g_inf_infectedSpeed` / `g_inf_convertedSpeed` | 1.15 / 1.0 | speed factor (on top of the Punchy's 1.3) |
| `g_inf_infectedArmor` / `g_inf_convertedArmor` | 100 / 0 | spawn armour |
| `g_inf_surviveBonus` | 5 | points per survivor alive at the end |
| `g_inf_botHoldLead` | 30 | seconds before the release at which survivor bots take positions |
| `g_inf_botEscort` | 2 | bots that seek out each human survivor |
| `g_inf_botJoinOnSight` | 1 | other survivor bots join a human they see |
| `g_inf_botAwareness` | 1 | 1 = infected bots know only fired/seen/pinged positions, 0 = always |
| `g_inf_pingInterval` | 15 | seconds between pings (0 = never) |
| `g_inf_adaptive` | 1 | difficulty follows the human players |
| `g_inf_level` | 0 | current difficulty level (-4..6) |
| `g_inf_debugHuman` | -1 | test only: treat this bot client as a human |

## Build from source
`./build_mod.sh <WoP source checkout>` applies `src/infection.patch` + `src/g_infection.c` (made against the commit in
`src/WOP_COMMIT`), builds `qagame.qvm` with the repo's own q3lcc/q3asm and writes `dist/infection/` and
`dist/wop_infection_mod.zip`. `test_mod.sh <WoP source checkout>` runs a short bot match on the dedicated server and
checks the round flow, the hold positions and the pickups in `games.log`. The human-only rules are tested with a
stand-in: `EXTRA='set g_inf_debugHuman 0;set g_inf_humanRole 1' ./test_mod.sh <src>` (role, escorts, joins, level).

The game code is GPL-2.0 like WoP's; the patch and the new file are inside the pk3 (`src/`).

`client_shot.sh <WoP source> <outdir> <client args>` runs the real client headless (Xvfb + software GL) and
screenshots a menu; the Create Game screen was checked this way (`+ui_creategame` opens it from the console).

## How it is wired (for later changes)
- Menu (`ui_startserver.c`): "Infection" is an extra entry of `gametype_items` mapped to `GT_TEAM`; on Fight it sets
  `g_infection`, `g_inf_humanRole`, `g_inf_prepTime`, auto-join and `bot_minplayers`. The two extra rows share the
  positions of Friendly Fire / Start Lives and are hidden for other game types. `ui_createInfection` remembers it.
- `g_infection.c`: round state machine (IDLE, PREP, HUNT, END), a role per client (survivor, waiting, infected) and
  `INF_SyncRoles()` which keeps teams equal to roles every frame.
- Hooks: `G_RunFrame` (round logic), `player_die` (infect), `G_Respawn` (team switch before the spawn), `SetTeam` (team
  requests), `ClientSpawn` (loadout), `Touch_Item` (pickups), `CheckGauntletAttack` (damage, reach), `ClientThink`
  (speed), `AddScore` (team score = rounds), `CheckTournament` (no warm-up), `G_CheckMinimumPlayers` (bots as one pool).
- Bots (`ai_dmnet.c`): `BotInfectionHuntGoal` (infected go to the nearest known survivor position),
  `BotInfectionHoldGoal` (survivors escort a human or hold a spot; returns "stand" when in position);
  `BotWantsToChase`/`BotWantsToRetreat` in `ai_dmq3.c`; `BotChooseWeapon` falls back to the Punchy when the weapon weights
  return nothing (stock code left weapon 0 selected: "weapon number (0) out of range").

## Not checked
- Seen on the real client (headless): the Create Game screen with the Infection entry and its two rows, and that picking
  the mod at run time loads the menu and `autoexec.cfg`. Not exercised: pressing Fight from the menu (no input device),
  the Mods menu list itself, and everything in a running game (centre-screen messages, sounds, the view of a waiting
  infected).
- The human rules (role, escort, join on sight, level) were tested with a bot standing in as the human
  (`g_inf_debugHuman`), not with a real player.
- Both QVMs are built from WoP source at the commit in `src/WOP_COMMIT` (version 1.7.1 in the source); an older
  installed WoP may not match.
