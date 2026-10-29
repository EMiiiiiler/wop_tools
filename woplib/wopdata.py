"""Facts about World of Padman that every generator and checker needs (checked against the WoP repo, Oct 2026)."""

WEAPONS = ('balloony', 'betty', 'boaster', 'bubbleg', 'imperius', 'pumper', 'splasher')
# bot item weights (WoP botfiles/fw_items.c): bots ignore low-weight weapons on pad-only / dead-end spots
WEAPON_WEIGHT = {'bubbleg': 400, 'boaster': 800, 'splasher': 900, 'pumper': 1000, 'betty': 1200, 'balloony': 1200,
                 'imperius': 1600}
MARKERS = ('orange', 'green', 'blue', 'black', 'purple')
POWERUPS = ('item_padpower', 'item_speedy', 'item_jumper', 'item_climber', 'item_visionless', 'item_revival')
HOLDABLES = ('holdable_floater', 'holdable_killerducks', 'holdable_boomies', 'holdable_bambam')
ARMOUR = ('item_armor_padshield', 'item_armor_shard')
# never place: the server segfaults on pickup (g_items.c Pickup_Powerup calls G_ForceClientWeapon on the item entity)
FORBIDDEN = {'item_berserker': 'WoP server segfaults on pickup (g_items.c bug)',
             'item_health': 'WoP has no health pickups (use station_health)',
             'item_health_large': 'WoP has no health pickups (use station_health)'}

PICKUPS = (tuple('weapon_' + w for w in WEAPONS) + tuple('ammo_' + w for w in WEAPONS) + ('ammo_nipper',)
           + POWERUPS + HOLDABLES + ARMOUR)
SPAWNS = ('info_player_deathmatch', 'info_player_start', 'team_redspawn', 'team_bluespawn', 'team_redplayer', 'team_blueplayer')
CTL = ('team_CTL_redlolly', 'team_CTL_bluelolly', 'team_CTL_neutrallolly')

# point/brush entities the generators use; anything else should be checked against WoP's entities.def first
KNOWN_CLASSES = set(PICKUPS + SPAWNS + CTL + (
    'worldspawn', 'light', 'info_player_intermission', 'misc_model', 'misc_externalmodel', 'misc_teleporter_dest', 'station_health',
    'target_position', 'target_speaker', 'target_push', 'target_score', 'target_teleporter', 'target_relay', 'target_delay',
    'target_print', 'target_location', 'info_null', 'info_notnull', 'path_corner',
    'trigger_push', 'trigger_multiple', 'trigger_teleport', 'trigger_hurt', 'trigger_always',
    'func_rotating', 'func_pendulum', 'func_bobbing', 'func_plat', 'func_train', 'func_door', 'func_button',
    'func_static', 'func_timer', 'func_group'))

# arena "type" tokens and what each needs in the map
ARENA_TYPES = ('ffa', 'lps', 'team', 'ft', 'ctkd', 'ctl', '1lc', 'syc_ffa', 'syc_tp', 'bb')
ARENA_NEEDS = {'ctl': ('team_CTL_redlolly', 'team_CTL_bluelolly'),
               '1lc': ('team_CTL_neutrallolly',)}

# sound/world/<x>.ogg (or .wav) files that exist in WoP (used on earlier maps; the online catalog lists newer
# sounds/maps/... names, check those exist before use)
SOUNDS = {
    'ambient': ('fire_crackling', 'fire_sizzling', 'wind_icy', 'wind_night', 'water_rippling', 'water_drippling',
                'water_drain', 'water_shower', 'water_bubbling', 'water_bubble', 'water_flowing', 'slime_bubbling',
                'floor_creaking', 'train_intercity', 'police_pass'),
    'machine': ('clock_ticking', 'fog_horn', 'fishtank', 'transformer', 'electric_sizzle', 'fan_pc', 'aircon',
                'ventilation', 'freezer', 'tv_upstairs', 'mechanics', 'dingdong'),
    'misc': ('wind_chimes', 'secret_found', 'alarm_buzzer', 'bicycle_bell', 'door_buzzer', 'toilet_flush'),
    'human': ('applause', 'footsteps_m', 'snoring'),
    'animal': ('bird_owl1', 'cricket_chirp1', 'cicada_chirp', 'dog_bark2', 'kitten_meow', 'bird_blackcap', 'blackbird'),
}
KNOWN_SOUNDS = {f'sound/world/{k}/{n}' for k, v in SOUNDS.items() for n in v} | {'sound/items/jumper/boing'}

# WoP common shaders (wop/scripts.pk3dir/scripts/common.shader). There is NO common/playerclip (it renders as a giant
# missing-texture grid). Unlike Quake 3, WoP's common/nodraw is NONSOLID: use common/caulk or common/weapclip for
# invisible collision. common/clip = playerclip (nonsolid for items and shots); *clip variants add footstep sounds.
COMMON = ('common/alpha_000', 'common/alpha_025', 'common/alpha_050', 'common/alpha_075', 'common/alpha_085', 'common/alpha_100',
          'common/caulk', 'common/lavacaulk', 'common/slimecaulk', 'common/watercaulk', 'common/botclip', 'common/carpetclip',
          'common/clip', 'common/cushion', 'common/full_clip', 'common/latticeclip', 'common/metalclip', 'common/missileclip',
          'common/sandclip', 'common/snowclip', 'common/softclip', 'common/splashclip', 'common/weapclip', 'common/woodclip',
          'common/donotenter', 'common/nodraw', 'common/nodrawnonsolid', 'common/nodrop', 'common/noimpact',
          'common/nolightmap', 'common/antiportal', 'common/areaportal', 'common/clusterportal', 'common/hint',
          'common/hintlocal', 'common/skip', 'common/hintskip', 'common/invisible', 'common/mirror1', 'common/portal',
          'common/slick', 'common/terrain', 'common/terrain2', 'common/origin', 'common/trigger', 'common/lightgrid')
NONSOLID_COMMON = ('common/nodraw', 'common/nodrawnonsolid', 'common/clip', 'common/botclip', 'common/trigger',
                   'common/origin', 'common/hint', 'common/skip', 'common/donotenter')

# skies shipped with WoP (env/<name>_rt.jpg ...)
SKIES = {'env/fort-pad512': 'sunny garden', 'env/pf-garden512': 'night sky', 'env/frost-bite512': 'snowy evening forest',
         'env/pc-friday-13th-512': 'night city'}

PLAYER = dict(w=30, h_stand=56, h_crouch=40, eye=26, origin_z=24, step=18, barrier=33)


# surfaceparms of every WoP common shader (from wop/scripts.pk3dir/scripts/common.shader, Oct 2026). audit_map/lint_map
# fall back to these when the game's scripts are not passed with --shaders.
COMMON_PARMS = {
    'common/alpha_000': ('nodraw', 'nonsolid', 'trans'),
    'common/alpha_025': ('nodraw', 'nonsolid', 'trans'),
    'common/alpha_050': ('nodraw', 'nonsolid', 'trans'),
    'common/alpha_075': ('nodraw', 'nonsolid', 'trans'),
    'common/alpha_085': ('nodraw', 'nonsolid', 'trans'),
    'common/alpha_100': ('nodraw', 'nonsolid', 'trans'),
    'common/antiportal': ('antiportal', 'nodraw', 'noimpact', 'nonsolid', 'structural', 'trans'),
    'common/areaportal': ('areaportal', 'nodraw', 'nolightmap', 'nomarks', 'nonsolid', 'structural', 'trans'),
    'common/botclip': ('botclip', 'nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'trans'),
    'common/carpetclip': ('carpetsteps', 'nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'trans'),
    'common/caulk': ('nodraw', 'nolightmap', 'nomarks'),
    'common/clip': ('nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'trans'),
    'common/clusterportal': ('clusterportal', 'nodraw', 'nolightmap', 'nomarks', 'nonsolid', 'trans'),
    'common/cushion': ('nodamage', 'nodraw', 'nolightmap', 'nomarks', 'trans'),
    'common/donotenter': ('donotenter', 'nodraw', 'nomarks', 'nonsolid', 'trans'),
    'common/full_clip': ('nodraw', 'playerclip'),
    'common/hint': ('hint', 'nodraw', 'noimpact', 'nonsolid', 'structural', 'trans'),
    'common/hintlocal': ('nodraw', 'noimpact', 'nonsolid', 'structural', 'trans'),
    'common/hintskip': ('nodraw', 'noimpact', 'nonsolid', 'skip', 'structural', 'trans'),
    'common/invisible': ('nolightmap',),
    'common/latticeclip': ('latticesteps', 'nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'trans'),
    'common/lavacaulk': ('lava', 'nodraw', 'nonsolid', 'trans'),
    'common/lightgrid': ('detail', 'lightgrid', 'nodraw', 'nolightmap', 'nomarks', 'nonsolid', 'trans'),
    'common/metalclip': ('metalsteps', 'nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'trans'),
    'common/mirror1': ('nolightmap',),
    'common/missileclip': ('nodamage', 'nodraw', 'nomarks', 'playerclip', 'trans'),
    'common/nodraw': ('nodraw', 'nolightmap', 'nomarks', 'nonsolid', 'trans'),
    'common/nodrawnonsolid': ('nodraw', 'nolightmap', 'nonsolid'),
    'common/nodrop': ('nodraw', 'nodrop', 'nolightmap', 'nomarks', 'nonsolid', 'trans'),
    'common/noimpact': ('noimpact',),
    'common/nolightmap': ('nolightmap',),
    'common/origin': ('nodraw', 'nolightmap', 'nonsolid', 'origin', 'trans'),
    'common/portal': ('nolightmap',),
    'common/sandclip': ('nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'sandsteps', 'trans'),
    'common/skip': ('nodraw', 'noimpact', 'nonsolid', 'skip', 'structural', 'trans'),
    'common/slick': ('nodraw', 'nolightmap', 'nomarks', 'slick', 'trans'),
    'common/slimecaulk': ('nodraw', 'nonsolid', 'slime', 'trans'),
    'common/snowclip': ('nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'snowsteps', 'trans'),
    'common/softclip': ('nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'softsteps', 'trans'),
    'common/splashclip': ('nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'splashsteps', 'trans'),
    'common/terrain': ('nodraw', 'nolightmap', 'nomarks'),
    'common/terrain2': ('dust', 'nodraw', 'nolightmap', 'nomarks'),
    'common/trigger': ('nodraw',),
    'common/watercaulk': ('nodraw', 'nonsolid', 'trans', 'water'),
    'common/weapclip': ('nodraw', 'nolightmap', 'nomarks', 'trans'),
    'common/woodclip': ('nodraw', 'noimpact', 'nolightmap', 'nomarks', 'nonsolid', 'playerclip', 'trans', 'woodsteps')
}
