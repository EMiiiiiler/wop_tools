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

static int INF_PickRandom(infRole_t role, qboolean avoidLast) {
	int i, n = 0, candidates[MAX_CLIENTS];

	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] != role)
			continue;
		if (avoidLast && infWasFirst[i])
			continue;
		candidates[n++] = i;
	}
	if (!n)
		return avoidLast ? INF_PickRandom(role, qfalse) : -1;
	return candidates[rand() % n];
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
		if (infRole[i] != IR_NONE)
			infRole[i] = IR_SURVIVOR;
	}

	n = g_inf_startInfected.integer;
	if (n <= 0)
		n = (players >= 6) ? 2 : 1;
	if (n > players - 1)
		n = players - 1;

	while (n-- > 0) {
		int c = INF_PickRandom(IR_SURVIVOR, qtrue);
		if (c < 0)
			break;
		infRole[c] = IR_WAITING;
		picked[c] = qtrue;
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
	INF_Print(va("^3Infection round %i^7: the infected arrive in ^3%i^7 seconds.", infRound, g_inf_prepTime.integer));
	G_LogPrintf("InfectionRound: %i start, %i players\n", infRound, players);
}

static void INF_Release(void) {
	int i;

	if (!INF_Count(IR_WAITING)) {
		// the picked infected left during the preparation
		int c = INF_PickRandom(IR_SURVIVOR, qfalse);
		if (c >= 0)
			infRole[c] = IR_WAITING;
	}

	INF_SetState(INF_HUNT);
	for (i = 0; i < level.maxclients; i++) {
		if (infRole[i] != IR_WAITING)
			continue;
		infRole[i] = IR_INFECTED;
		INF_MoveClient(g_entities + i, TEAM_RED);
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
	INF_GlobalSound(INF_SND_END);
	CalculateRanks();
	SendScoreboardMessageToAllClients();
	G_LogPrintf("InfectionRound: %i end, %s win\n", infRound, winner == TEAM_RED ? "infected" : "survivors");
	INF_SetState(INF_END);
}

static void INF_RunPrep(void) {
	int i, sec;
	int remaining = g_inf_prepTime.integer * 1000 - (level.time - infStateTime);

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
		int c = INF_PickRandom(IR_SURVIVOR, qfalse);
		if (c < 0)
			return;
		infRole[c] = IR_INFECTED;
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

	if (survivors == 1 && !infLastAnnounced && INF_NumPlayers() > 2) {
		int c = INF_PickRandom(IR_SURVIVOR, qfalse);
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
	if (!INF_IsInfected(client))
		return;
	client->ps.stats[STAT_WEAPONS] = (1 << WP_PUNCHY);
	client->ps.ammo[WP_NIPPER] = 0;
	client->ps.ammo[WP_PUNCHY] = -1;
	client->ps.stats[STAT_ARMOR] = g_inf_infectedArmor.integer;
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
