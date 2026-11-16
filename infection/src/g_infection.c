/*
===========================================================================
Infection for World of Padman - a server-side modifier for Free For All Team (g_gametype 6).

This file is free software; you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation; either version 2 of
the License, or (at your option) any later version.
===========================================================================

Round flow (g_infection 1, g_gametype GT_TEAM):
  PREP  everybody but the picked infected plays as a survivor (Blue Noses) and has g_inf_prepTime
        seconds to collect weapons and find a place to defend. The picked infected wait as free-flying
        spectators.
  HUNT  the infected are released as Red Pads with nothing but the Punchy. A survivor who dies - however -
        respawns as infected. The round ends when nobody is left (infected win) or after g_inf_roundTime
        seconds (survivors win).
  END   a short pause, then the next round with new infected.
Team scores count rounds won (red = infected, blue = survivors), so pointlimit = rounds to win.
*/

#include "g_local.h"

typedef enum { INF_IDLE, INF_PREP, INF_HUNT, INF_END } infState_t;
typedef enum { IR_NONE, IR_SURVIVOR, IR_WAITING, IR_INFECTED } infRole_t;

#define INF_END_PAUSE 6000
#define INF_SND_RELEASE "sound/feedback/lets_rock.wav"
#define INF_SND_TEN "sound/feedback/ten_seconds.wav"
#define INF_SND_LAST "sound/feedback/sudden_death.wav"
#define INF_SND_END "sound/feedback/game_over.wav"

static infState_t infState;
static int infStateTime;
static int infLastSecond;
static int infRound;
static qboolean infLastAnnounced;
static infRole_t infRole[MAX_CLIENTS];
static qboolean infWasFirst[MAX_CLIENTS]; // picked as first infected in the previous round
static qboolean infAlpha[MAX_CLIENTS];	  // first infected of this round: they get the speed, armour and reach buffs

static vec3_t infKnownPos[MAX_CLIENTS];	  // where the infected bots last heard or saw a survivor
static int infKnownTime[MAX_CLIENTS];	  // 0 = they have no idea
static int infNextPing;
static int infThreat;					  // adaptive difficulty of this round: > 0 stronger infected, < 0 stronger survivors
static qboolean infHumanInfected;		  // a human started this round as infected

#define INF_LEVEL_MIN -4
#define INF_LEVEL_MAX 6

#define INF_PICK_ANY 0
#define INF_PICK_BOTS 1
#define INF_PICK_HUMANS 2

static qboolean INF_IsBot(int clientNum) {
	// g_inf_debugHuman <client>: treat that bot as a human, to test the human rules on a dedicated server
	if (clientNum == g_inf_debugHuman.integer)
		return qfalse;
	return (g_entities[clientNum].r.svFlags & SVF_BOT) ? qtrue : qfalse;
}

qboolean INF_IsHumanPlayer(int clientNum) {
	return INF_IsBot(clientNum) ? qfalse : qtrue;
}

void INF_Reveal(int clientNum);

qboolean G_Infection(void) {
	return (g_infection.integer && g_gametype.integer == GT_TEAM) ? qtrue : qfalse;
}

qboolean INF_IsInfected(const gclient_t *client) {
	return (G_Infection() && client && client->sess.sessionTeam == TEAM_RED) ? qtrue : qfalse;
}

static void INF_GlobalSound(const char *name) {
	gentity_t *te = G_TempEntity(vec3_origin, EV_GLOBAL_SOUND);
	te->s.eventParm = G_SoundIndex(name);
	te->r.svFlags |= SVF_BROADCAST;
}

static void INF_Print(const char *msg) {
	trap_SendServerCommand(-1, va("print \"%s\n\"", msg));
}

static void INF_CenterPrint(int clientNum, const char *msg) {
	trap_SendServerCommand(clientNum, va("cp \"%s\n\"", msg));
}

static int INF_Count(infRole_t role) {
	int i, n = 0;
	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] == role)
			n++;
	}
	return n;
}

static int INF_NumPlayers(void) {
	return INF_Count(IR_SURVIVOR) + INF_Count(IR_WAITING) + INF_Count(IR_INFECTED);
}

static void INF_SetState(infState_t state) {
	infState = state;
	infStateTime = level.time;
	infLastSecond = -1;
}

/*
Put a client on a team without the suicide, the score penalty and the broadcast of SetTeam()
*/
static void INF_MoveClient(gentity_t *ent, team_t team) {
	gclient_t *client = ent->client;
	int clientNum = client - level.clients;
	int oldTeam = client->sess.sessionTeam;

	if (client->pers.connected != CON_CONNECTED)
		return;

	if (oldTeam != TEAM_SPECTATOR) {
		if (client->ps.stats[STAT_HEALTH] <= 0)
			CopyToBodyQue(ent);
		RemoveOwnedItems(ent);
	}

	client->pers.teamState.state = TEAM_BEGIN;
	client->sess.sessionTeam = team;
	client->sess.spectatorState = (team == TEAM_SPECTATOR) ? SPECTATOR_FREE : SPECTATOR_NOT;
	client->sess.spectatorClient = 0;
	client->sess.teamLeader = qfalse;

	if (team == TEAM_RED || team == TEAM_BLUE) {
		int teamLeader = TeamLeader(team);
		if (teamLeader == -1 ||
			(!(g_entities[clientNum].r.svFlags & SVF_BOT) && (g_entities[teamLeader].r.svFlags & SVF_BOT))) {
			SetLeader(team, clientNum);
		}
	}
	if (oldTeam == TEAM_RED || oldTeam == TEAM_BLUE)
		CheckTeamLeader(oldTeam);

	ClientUserinfoChanged(clientNum);
	ClientBegin(clientNum);
}

/*
Keeps roles and teams in step: new players get a role, nobody sits on the wrong team.
*/
static void INF_SyncRoles(void) {
	int i;

	for (i = 0; i < level.maxclients; i++) {
		gclient_t *cl = level.clients + i;
		gentity_t *ent = g_entities + i;
		team_t want;

		if (cl->pers.connected != CON_CONNECTED) {
			if (cl->pers.connected == CON_DISCONNECTED) {
				infRole[i] = IR_NONE;
				infWasFirst[i] = qfalse;
				infAlpha[i] = qfalse;
			}
			continue;
		}

		if (cl->sess.sessionTeam == TEAM_SPECTATOR) {
			if (infRole[i] != IR_WAITING)
				infRole[i] = IR_NONE;
			continue;
		}

		if (infRole[i] == IR_WAITING) {
			// somebody forced a waiting infected onto a team
			INF_MoveClient(ent, TEAM_SPECTATOR);
			continue;
		}

		if (infRole[i] == IR_NONE)
			infRole[i] = (infState == INF_HUNT || infState == INF_END) ? IR_INFECTED : IR_SURVIVOR;

		want = (infRole[i] == IR_INFECTED) ? TEAM_RED : TEAM_BLUE;
		if (cl->sess.sessionTeam == want)
			continue;

		if (cl->ps.stats[STAT_HEALTH] <= 0) {
			// a freshly infected survivor: INF_PreRespawn switches the team, don't let them wait it out
			if (level.time > cl->respawnTime + 1000)
				G_Respawn(ent);
			continue;
		}
		INF_MoveClient(ent, want);
	}
}

/*
Random client with the given role. prefer: bots or humans first (g_inf_humanRole), falling back to anybody.
*/
static int INF_PickRandom(infRole_t role, qboolean avoidLast, int prefer) {
	int i, n = 0, candidates[MAX_CLIENTS];

	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] != role)
			continue;
		if (avoidLast && infWasFirst[i])
			continue;
		if (prefer == INF_PICK_BOTS && !INF_IsBot(i))
			continue;
		if (prefer == INF_PICK_HUMANS && INF_IsBot(i))
			continue;
		candidates[n++] = i;
	}
	if (n)
		return candidates[rand() % n];
	if (avoidLast)
		return INF_PickRandom(role, qfalse, prefer);
	if (prefer != INF_PICK_ANY)
		return INF_PickRandom(role, qfalse, INF_PICK_ANY);
	return -1;
}

/*
g_inf_humanRole: 0 = humans are picked like everybody else, 1 = humans always start as survivors,
2 = humans always start as infected
*/
static int INF_FirstPickPreference(void) {
	if (g_inf_humanRole.integer == 1)
		return INF_PICK_BOTS;
	if (g_inf_humanRole.integer == 2)
		return INF_PICK_HUMANS;
	return INF_PICK_ANY;
}

static int INF_CountHumans(infRole_t role) {
	int i, n = 0;

	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] == role && !INF_IsBot(i))
			n++;
	}
	return n;
}

/*
The preparation is shortened when no human is left among the survivors (nobody wants to watch bots shop)
*/
static int INF_PrepTime(void) {
	int prep = g_inf_prepTime.integer;

	if (g_inf_infectedPrepTime.integer >= 0 && g_inf_infectedPrepTime.integer < prep && INF_CountHumans(IR_WAITING) &&
		!INF_CountHumans(IR_SURVIVOR))
		prep = g_inf_infectedPrepTime.integer;
	return prep;
}

static void INF_Abort(void) {
	int i;

	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] == IR_NONE)
			continue;
		infRole[i] = IR_SURVIVOR;
		if (level.clients[i].sess.sessionTeam != TEAM_BLUE)
			INF_MoveClient(g_entities + i, TEAM_BLUE);
	}
	INF_SetState(INF_IDLE);
}

static void INF_StartRound(void) {
	int i, n, players, picked[MAX_CLIENTS];

	players = INF_NumPlayers();
	for (i = 0; i < level.maxclients; i++) {
		picked[i] = qfalse;
		infAlpha[i] = qfalse;
		if (infRole[i] != IR_NONE)
			infRole[i] = IR_SURVIVOR;
	}

	n = g_inf_startInfected.integer;
	if (n <= 0)
		n = (players >= 6) ? 2 : 1;

	infThreat = 0;
	infHumanInfected = qfalse;
	for (i = 0; i < n && i < players - 1; i++) {
		int c, prefer = INF_FirstPickPreference();

		// once the round is set up as "humans survive", the extra infected are bots
		if (i > 0 && !infHumanInfected && prefer == INF_PICK_ANY && INF_CountHumans(IR_SURVIVOR))
			prefer = INF_PICK_BOTS;
		// "always infected" beats "not twice in a row" for humans
		c = INF_PickRandom(IR_SURVIVOR, g_inf_humanRole.integer != 2, prefer);
		if (c < 0)
			break;
		infRole[c] = IR_WAITING;
		infAlpha[c] = qtrue;
		picked[c] = qtrue;

		if (i == 0) {
			// adaptive difficulty: the level works for whichever side the humans are on
			infHumanInfected = INF_IsBot(c) ? qfalse : qtrue;
			if (g_inf_adaptive.integer && (infHumanInfected || INF_CountHumans(IR_SURVIVOR))) {
				int lvl = g_inf_level.integer;
				if (lvl < INF_LEVEL_MIN)
					lvl = INF_LEVEL_MIN;
				if (lvl > INF_LEVEL_MAX)
					lvl = INF_LEVEL_MAX;
				infThreat = infHumanInfected ? -lvl : lvl;
				// every two levels of threat bring one more infected, up to half of the players
				if (infThreat > 0) {
					n += infThreat / 2;
					if (n > players / 2)
						n = players / 2;
				}
			}
		}
	}

	for (i = 0; i < level.maxclients; i++) {
		infWasFirst[i] = picked[i];
		if (infRole[i] == IR_WAITING)
			INF_MoveClient(g_entities + i, TEAM_SPECTATOR);
		else if (infRole[i] == IR_SURVIVOR)
			INF_MoveClient(g_entities + i, TEAM_BLUE); // fresh spawn, start inventory
	}

	infRound++;
	infLastAnnounced = qfalse;
	INF_SetState(INF_PREP);
	INF_Print(va("^3Infection round %i^7: the infected arrive in ^3%i^7 seconds.", infRound, INF_PrepTime()));
	G_LogPrintf("InfectionRound: %i start, %i players\n", infRound, players);
	if (g_inf_adaptive.integer && (infHumanInfected || INF_CountHumans(IR_SURVIVOR))) {
		INF_Print(va("Difficulty level ^3%i^7.", g_inf_level.integer));
		G_LogPrintf("InfectionLevel: %i threat %i\n", g_inf_level.integer, infThreat);
	}
}

static void INF_Release(void) {
	int i;

	if (!INF_Count(IR_WAITING)) {
		// the picked infected left during the preparation
		int c = INF_PickRandom(IR_SURVIVOR, qfalse, g_inf_humanRole.integer == 1 ? INF_PICK_BOTS : INF_PICK_ANY);
		if (c >= 0) {
			infRole[c] = IR_WAITING;
			infAlpha[c] = qtrue;
		}
	}

	INF_SetState(INF_HUNT);
	memset(infKnownTime, 0, sizeof(infKnownTime));
	infNextPing = level.time + g_inf_pingInterval.integer * 1000;
	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] != IR_WAITING)
			continue;
		infRole[i] = IR_INFECTED;
		INF_MoveClient(g_entities + i, TEAM_RED);
		G_LogPrintf("InfectionFirst: %i\n", i);
		INF_Print(va("%s ^7is ^1INFECTED^7.", level.clients[i].pers.netname));
		INF_CenterPrint(i, "You are ^1INFECTED^7!\nPunch the survivors.");
	}
	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] == IR_SURVIVOR)
			INF_CenterPrint(i, "^1The infected are loose!");
	}
	INF_GlobalSound(INF_SND_RELEASE);
	G_LogPrintf("InfectionRelease: %i infected, %i survivors\n", INF_Count(IR_INFECTED), INF_Count(IR_SURVIVOR));
}

static void INF_EndRound(team_t winner) {
	int i;

	level.teamScores[winner]++;
	if (winner == TEAM_BLUE) {
		for (i = 0; i < level.maxclients; i++) {
			if (infRole[i] == IR_SURVIVOR) {
				AddScore(g_entities + i, g_entities[i].r.currentOrigin, g_inf_surviveBonus.integer, "survived");
				INF_Print(va("%s ^7survived.", level.clients[i].pers.netname));
			}
		}
		trap_SendServerCommand(-1, "cp \"^4The survivors win the round!\n\"");
	} else {
		trap_SendServerCommand(-1, "cp \"^1Everyone is infected!\n\"");
	}
	if (g_inf_adaptive.integer && (infHumanInfected || INF_CountHumans(IR_SURVIVOR) || INF_CountHumans(IR_INFECTED))) {
		// the humans did well: infected humans wiped the survivors, or a human survivor lived to the end
		qboolean humansWon = infHumanInfected ? (winner == TEAM_RED) : (INF_CountHumans(IR_SURVIVOR) > 0);
		int lvl = g_inf_level.integer + (humansWon ? 1 : -1);

		if (lvl < INF_LEVEL_MIN)
			lvl = INF_LEVEL_MIN;
		if (lvl > INF_LEVEL_MAX)
			lvl = INF_LEVEL_MAX;
		trap_Cvar_Set("g_inf_level", va("%i", lvl));
		trap_Cvar_Update(&g_inf_level);
		INF_Print(va("Next round: difficulty level ^3%i^7.", lvl));
	}
	INF_GlobalSound(INF_SND_END);
	CalculateRanks();
	SendScoreboardMessageToAllClients();
	G_LogPrintf("InfectionRound: %i end, %s win\n", infRound, winner == TEAM_RED ? "infected" : "survivors");
	INF_SetState(INF_END);
}

static void INF_RunPrep(void) {
	int i, sec;
	int remaining = INF_PrepTime() * 1000 - (level.time - infStateTime);

	if (remaining <= 0) {
		INF_Release();
		return;
	}

	sec = (remaining + 999) / 1000;
	if (sec == infLastSecond)
		return;
	infLastSecond = sec;

	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] == IR_WAITING) {
			INF_CenterPrint(i, va("You are ^1INFECTED^7\nYou will be released in ^3%i", sec));
		} else if (infRole[i] == IR_SURVIVOR && (sec <= 10 || sec % 30 == 0)) {
			if (sec <= 10)
				INF_CenterPrint(i, va("The infected arrive in ^3%i", sec));
			else
				INF_CenterPrint(i, va("The infected arrive in ^3%i^7 seconds\nGrab weapons and find a place to defend!", sec));
		}
	}
	if (sec == 10)
		INF_GlobalSound(INF_SND_TEN);
}

static void INF_RunHunt(void) {
	int survivors = INF_Count(IR_SURVIVOR);

	if (!survivors) {
		INF_EndRound(TEAM_RED);
		return;
	}

	if (!INF_Count(IR_INFECTED)) {
		// every infected left the game
		int c = INF_PickRandom(IR_SURVIVOR, qfalse, g_inf_humanRole.integer == 1 ? INF_PICK_BOTS : INF_PICK_ANY);
		if (c < 0)
			return;
		infRole[c] = IR_INFECTED;
		infAlpha[c] = qtrue;
		INF_MoveClient(g_entities + c, TEAM_RED);
		INF_Print(va("%s ^7is ^1INFECTED^7.", level.clients[c].pers.netname));
		INF_CenterPrint(c, "You are ^1INFECTED^7!\nPunch the survivors.");
		return;
	}

	if (g_inf_roundTime.integer > 0) {
		int remaining = g_inf_roundTime.integer * 1000 - (level.time - infStateTime);
		int sec = (remaining + 999) / 1000;

		if (remaining <= 0) {
			INF_EndRound(TEAM_BLUE);
			return;
		}
		if (sec != infLastSecond) {
			infLastSecond = sec;
			if (sec == 60 || sec == 30 || sec == 10)
				trap_SendServerCommand(-1, va("cp \"^3%i^7 seconds until the survivors win\n\"", sec));
		}
	}

	if (g_inf_pingInterval.integer > 0 && level.time >= infNextPing) {
		// now and then the infected sense where everybody is
		int i;

		infNextPing = level.time + g_inf_pingInterval.integer * 1000;
		for (i = 0; i < level.maxclients; i++) {
			if (infRole[i] == IR_SURVIVOR)
				INF_Reveal(i);
		}
	}

	if (survivors == 1 && !infLastAnnounced && INF_NumPlayers() > 2) {
		int c = INF_PickRandom(IR_SURVIVOR, qfalse, INF_PICK_ANY);
		infLastAnnounced = qtrue;
		trap_SendServerCommand(-1, va("cp \"%s ^7is the last Pad standing!\n\"", level.clients[c].pers.netname));
		INF_GlobalSound(INF_SND_LAST);
	}
}

void INF_RunFrame(void) {
	if (!G_Infection() || level.intermissiontime || level.restarted)
		return;

	INF_SyncRoles();

	if (infState != INF_IDLE && INF_NumPlayers() < 2) {
		INF_Abort();
		INF_Print("Infection needs at least two players.");
		return;
	}

	switch (infState) {
	case INF_IDLE:
		if (INF_NumPlayers() >= 2)
			INF_StartRound();
		break;
	case INF_PREP:
		INF_RunPrep();
		break;
	case INF_HUNT:
		INF_RunHunt();
		break;
	case INF_END:
		if (level.time - infStateTime >= INF_END_PAUSE)
			INF_StartRound();
		break;
	}
}

void INF_Init(void) {
	memset(infRole, 0, sizeof(infRole));
	memset(infWasFirst, 0, sizeof(infWasFirst));
	memset(infAlpha, 0, sizeof(infAlpha));
	infRound = 0;
	infLastAnnounced = qfalse;
	INF_SetState(INF_IDLE);

	G_SoundIndex(INF_SND_RELEASE);
	G_SoundIndex(INF_SND_TEN);
	G_SoundIndex(INF_SND_LAST);
	G_SoundIndex(INF_SND_END);
}

/*
Called from player_die: a survivor who dies during the hunt is infected
*/
void INF_PlayerDied(gentity_t *self, gentity_t *attacker) {
	int clientNum;

	if (!G_Infection() || infState != INF_HUNT || !self->client)
		return;

	clientNum = self->client - level.clients;
	if (infRole[clientNum] != IR_SURVIVOR)
		return;

	infRole[clientNum] = IR_INFECTED;
	if (attacker && attacker->client && attacker != self && attacker->client->sess.sessionTeam == TEAM_RED) {
		INF_Print(va("%s ^7was ^1INFECTED^7 by %s^7.", self->client->pers.netname, attacker->client->pers.netname));
	} else {
		INF_Print(va("%s ^7is ^1INFECTED^7.", self->client->pers.netname));
	}
	INF_CenterPrint(clientNum, "You are ^1INFECTED^7!\nPunch the survivors.");
	G_LogPrintf("Infected: %i %i\n", clientNum, INF_Count(IR_SURVIVOR));
}

/*
Called from G_Respawn before the client is placed: an infected survivor comes back as a Red Pad
*/
void INF_PreRespawn(gentity_t *ent) {
	int clientNum;
	team_t want;

	if (!G_Infection() || !ent->client)
		return;

	clientNum = ent->client - level.clients;
	if (infRole[clientNum] != IR_INFECTED && infRole[clientNum] != IR_SURVIVOR)
		return;

	want = (infRole[clientNum] == IR_INFECTED) ? TEAM_RED : TEAM_BLUE;
	if (ent->client->sess.sessionTeam == want || ent->client->sess.sessionTeam == TEAM_SPECTATOR)
		return;

	ent->client->sess.sessionTeam = want;
	ent->client->sess.teamLeader = qfalse;
	ent->client->pers.teamState.state = TEAM_BEGIN;
	ClientUserinfoChanged(clientNum);
	CheckTeamLeader(TEAM_RED);
	CheckTeamLeader(TEAM_BLUE);
}

/*
Called from SetTeam for a request to join a playing team. Teams are assigned by the mode.
*/
qboolean INF_FilterTeamRequest(gentity_t *ent, int *team) {
	int clientNum = ent->client - level.clients;

	if (infRole[clientNum] == IR_WAITING) {
		INF_CenterPrint(clientNum, "You are ^1INFECTED^7\nWait for your release.");
		return qfalse;
	}
	if (ent->client->sess.sessionTeam == TEAM_RED || ent->client->sess.sessionTeam == TEAM_BLUE) {
		INF_CenterPrint(clientNum, "Infection assigns the teams.");
		return qfalse;
	}
	*team = (infState == INF_HUNT || infState == INF_END) ? TEAM_RED : TEAM_BLUE;
	return qtrue;
}

/*
The infected only have the Punchy
*/
void INF_SetLoadout(gclient_t *client) {
	int armor;

	if (!G_Infection())
		return;
	if (!INF_IsInfected(client)) {
		// adaptive difficulty in favour of the survivors: they start with some armour
		if (infThreat < 0 && client->sess.sessionTeam == TEAM_BLUE)
			client->ps.stats[STAT_ARMOR] = -20 * infThreat;
		return;
	}
	client->ps.stats[STAT_WEAPONS] = (1 << WP_PUNCHY);
	client->ps.ammo[WP_NIPPER] = 0;
	client->ps.ammo[WP_PUNCHY] = -1;
	armor = infAlpha[client - level.clients] ? g_inf_infectedArmor.integer : g_inf_convertedArmor.integer;
	armor += 15 * infThreat;
	client->ps.stats[STAT_ARMOR] = (armor > 0) ? armor : 0;
}

/*
The first infected of a round are stronger than the survivors they convert, so a round builds up to a last stand
*/
float INF_SpeedScale(const gclient_t *client) {
	float scale;

	if (!INF_IsInfected(client))
		return 1.0f;
	scale = infAlpha[client - level.clients] ? g_inf_infectedSpeed.value : g_inf_convertedSpeed.value;
	if (scale <= 0)
		scale = 1.0f;
	scale += 0.03f * infThreat;
	return (scale > 0.8f) ? scale : 0.8f;
}

int INF_MeleeRange(const gclient_t *client) {
	int range;

	if (!INF_IsInfected(client))
		return 32;
	range = infAlpha[client - level.clients] ? g_inf_meleeRange.integer : g_inf_convertedRange.integer;
	return (range > 32) ? range : 32;
}

/*
For the bots: 0 while the survivors still collect, else the round number (bots take up their positions
g_inf_botHoldLead seconds before the release and keep them during the hunt)
*/
int INF_HoldRound(void) {
	if (!G_Infection())
		return 0;
	if (infState == INF_HUNT)
		return infRound;
	if (infState == INF_PREP) {
		int prep = INF_PrepTime();
		int lead = g_inf_botHoldLead.integer;

		if (lead > prep / 2)
			lead = prep / 2;
		if (prep * 1000 - (level.time - infStateTime) <= lead * 1000)
			return infRound;
	}
	return 0;
}

qboolean INF_IsSurvivor(int clientNum) {
	return (G_Infection() && clientNum >= 0 && clientNum < MAX_CLIENTS && infRole[clientNum] == IR_SURVIVOR) ? qtrue
																										   : qfalse;
}

qboolean INF_CanPickup(const gentity_t *other, const gitem_t *item) {
	if (!INF_IsInfected(other->client))
		return qtrue;
	if (item->giType == IT_WEAPON || item->giType == IT_AMMO || item->giType == IT_HOLDABLE)
		return qfalse;
	return qtrue;
}

/*
Humans parked as spectators until the release still count as players for bot_minplayers
*/
int INF_CountWaitingHumans(void) {
	int i, n = 0;

	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] == IR_WAITING && level.clients[i].pers.connected == CON_CONNECTED &&
			!(g_entities[i].r.svFlags & SVF_BOT))
			n++;
	}
	return n;
}

/*
What the infected bots know (g_inf_botAwareness 1): a survivor gives its position away by firing, by being
seen, and every g_inf_pingInterval seconds. A bot that arrives and finds nobody forgets the position again.
With g_inf_botAwareness 0 they always know where everybody is.
*/
void INF_Reveal(int clientNum) {
	if (clientNum < 0 || clientNum >= MAX_CLIENTS || !g_entities[clientNum].client)
		return;
	VectorCopy(g_entities[clientNum].client->ps.origin, infKnownPos[clientNum]);
	infKnownTime[clientNum] = level.time;
}

void INF_Noise(const gentity_t *ent) {
	int clientNum;

	if (!G_Infection() || infState != INF_HUNT || !ent->client)
		return;
	clientNum = ent->client - level.clients;
	if (infRole[clientNum] == IR_SURVIVOR)
		INF_Reveal(clientNum);
}

qboolean INF_KnownPosition(int clientNum, vec3_t out) {
	if (!INF_IsSurvivor(clientNum) || g_entities[clientNum].health <= 0)
		return qfalse;
	if (!g_inf_botAwareness.integer) {
		VectorCopy(g_entities[clientNum].client->ps.origin, out);
		return qtrue;
	}
	if (!infKnownTime[clientNum])
		return qfalse;
	VectorCopy(infKnownPos[clientNum], out);
	return qtrue;
}

void INF_ForgetPosition(int clientNum) {
	if (clientNum >= 0 && clientNum < MAX_CLIENTS)
		infKnownTime[clientNum] = 0;
}

/*
Player models: every infected wears g_inf_infectedModel, and a survivor who picked that model gets
g_inf_survivorModel instead, so you can tell the two sides apart by their shape.
Model strings are "name" or "name/skin"; only the name before the slash is compared.
*/
static qboolean INF_SameModel(const char *a, const char *b) {
	while (*a && *a != '/' && *b && *b != '/') {
		if (tolower(*a) != tolower(*b))
			return qfalse;
		a++;
		b++;
	}
	return ((!*a || *a == '/') && (!*b || *b == '/')) ? qtrue : qfalse;
}

void INF_ForceModel(const gclient_t *client, char *model, int modelSize, char *headModel, int headModelSize) {
	if (!G_Infection() || !g_inf_infectedModel.string[0])
		return;

	if (client->sess.sessionTeam == TEAM_RED) {
		Q_strncpyz(model, g_inf_infectedModel.string, modelSize);
		Q_strncpyz(headModel, g_inf_infectedModel.string, headModelSize);
		return;
	}

	// survivors, and waiting infected / spectators who would otherwise show it on the scoreboard
	if (!g_inf_survivorModel.string[0] || INF_SameModel(g_inf_survivorModel.string, g_inf_infectedModel.string))
		return;
	if (INF_SameModel(model, g_inf_infectedModel.string))
		Q_strncpyz(model, g_inf_survivorModel.string, modelSize);
	if (INF_SameModel(headModel, g_inf_infectedModel.string))
		Q_strncpyz(headModel, g_inf_survivorModel.string, headModelSize);
}
