"""Глобални константи за играта ЕХО.

Сите „магични броеви“ живеат тука, за да се менуваат на едно место.
"""

# --- Прозорец ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# --- Бои (R, G, B) ---
COLOR_PLAYER = (120, 225, 255)
COLOR_DEBUG_WALL = (95, 85, 150)      # ѕидовите се гледаат САМО во debug режим
COLOR_EXIT = (120, 255, 180)

# --- Мапа ---
TILE_SIZE = 40                        # 32 x 18 плочки = 1280 x 720
LEVELS_DIR = "assets/levels"
# (датотека, клуч за името во ui/i18n.py)
LEVELS = [
    ("level1.txt", "level_1"),
    ("level2.txt", "level_2"),
    ("level3.txt", "level_3"),
]
TILE_WALL = "#"
TILE_FLOOR = "."
TILE_PLAYER = "P"
TILE_EXIT = "E"
EXIT_GLOW_RADIUS = 60
EXIT_PULSE_SPEED = 2.0                # колку брзо „дише“ сјајот на излезот

# --- Играч ---
PLAYER_RADIUS = 10
PLAYER_SPEED_WALK = 160    # пиксели во секунда
PLAYER_SPEED_SNEAK = 70    # со Shift: побавно, а подоцна и потивко
PLAYER_GLOW_RADIUS = 45    # колку далеку се шири сјајот околу играчот
PLAYER_AUTO_ROTATE = 110   # °/s: играчот сам постојано се врти (цел круг за ~3.3 s)

# --- Звук / ехо ---
SOUND_RAY_COUNT = 160          # колку зраци испушта секој звук (повеќе = помазни контури, побавно)
SOUND_WAVE_SPEED = 420         # колку брзо се шири бранот (пиксели во секунда)
SOUND_FADE_TIME = 2.2          # колку секунди свети ѕидот откако ќе го допре бранот

# Јачина на звукот = до каде стига бранот (во пиксели).
# Истата бројка подоцна ја користат чудовиштата: подалеку од ова не слушаат.
SOUND_STEP_WALK = 230
SOUND_STEP_SNEAK = 80
SOUND_CLAP = 520
SOUND_STONE = 340

STEP_INTERVAL_WALK = 0.42      # секунди меѓу два чекора
STEP_INTERVAL_SNEAK = 0.65
CLAP_COOLDOWN = 1.2

# --- Камчиња ---
STONE_COUNT = 5
STONE_SPEED = 600
STONE_MAX_DISTANCE = 420
STONE_RADIUS = 3
STONE_HIT_RADIUS = 6          # колку блиску до телото на чудовиштето = погодок (уништено)
STONE_SCARE_RADIUS = 120      # камче што паѓа поблиску од ова до чудовиште го плаши → бега
AIM_ASSIST_ANGLE = 15         # E: ако познато чудовиште е до толку степени од стрелката, камчето лета точно кон него
FLEE_TIME = 3.5               # најмногу толку секунди бега
FLEE_DISTANCE_TILES = 8       # колку далеку бара место за бегство
MONSTER_SPEED_FLEE = 170
SOUND_MONSTER_DEATH = 420     # звук на уништено чудовиште (ги осветлува ѕидовите)
AWARENESS_MEMORY = 6.0         # колку секунди играчот „памети“ каде последно го слушнал/видел чудовиштето

# Бои на брановите според видот на звукот.
COLOR_WAVE_STEP = (90, 200, 255)
COLOR_WAVE_CLAP = (220, 230, 255)
COLOR_WAVE_STONE = (255, 170, 80)
COLOR_STONE = (245, 245, 255)   # самото камче во лет е бело топче

# --- Чудовиште ---
TILE_MONSTER = "M"
MONSTER_RADIUS = 13
MONSTER_SPEED_PATROL = 55
MONSTER_SPEED_INVESTIGATE = 95
MONSTER_SPEED_HUNT = 185           # побрзо од играчот (160): не можеш само да избегаш
MONSTER_STEP_LOUDNESS = 150        # чекорите на чудовиштето се слушаат (црвени бранови)
MONSTER_STEP_INTERVAL_PATROL = 0.9
MONSTER_STEP_INTERVAL_HUNT = 0.35

# Слух: перцепирана јачина = јачина - растојание - (ѕидови * казна).
# Ако резултатот е > 0, чудовиштето го слушнало звукот.
HEARING_WALL_PENALTY = 110         # секој ѕид меѓу звукот и увото „јаде“ толку пиксели
HEARING_HUNT_THRESHOLD = 0.45      # над овој удел од јачината: директно лов
SEARCH_DURATION = 5.0              # колку секунди пребарува пред да се откаже
SEARCH_RADIUS_TILES = 3
PATROL_RADIUS_TILES = 8
REPATH_INTERVAL = 0.5              # во лов, патеката се пресметува најмногу 2x во секунда

SHRIEK_LOUDNESS = 620             # крикот се слуша далеку, ги вика и другите
SHRIEK_COOLDOWN = 8.0              # едно чудовиште не вреска почесто од ова
MONSTER_SEPARATION = 2.4           # чудовиштата се држат на толку радиуси едно од друго

# --- Директор (мозок 1) ---
DIRECTOR_CALM_PER_LEVEL = [14.0, 10.0, 7.0]   # по колку секунди мир директорот почнува да притиска
DIRECTOR_HINT_INTERVAL = 6.0       # најмалку толку секунди меѓу две насоки
DIRECTOR_HINT_DURATION = 12.0      # колку важи една насока
DIRECTOR_HINT_MAX_TILES = 7        # првата насока е нејасна (голема зона)...
DIRECTOR_HINT_MIN_TILES = 3        # ...а со текот на мирот станува сè попрецизна
DIRECTOR_RELAX_TIME = 9.0          # по лов: толку секунди одмор
DIRECTOR_EXIT_GUARD_DISTANCE = 300 # играч поблиску од ова до излезот → чувар на излезот

# --- Меморија на чудовиштата (SQLite) ---
MEMORY_DB = "echo_memory.db"
MEMORY_DECAY = 0.85                # по секоја партија старата меморија „бледнее“ за 15%
MEMORY_MIN_WEIGHT = 0.2            # послабо од ова се брише (заборавено)
MEMORY_SAMPLE_INTERVAL = 0.5       # на секои 0.5 s се бележи каде е играчот
MEMORY_SOUND_WEIGHT = 2.0          # звук што го направил играчот вреди двојно
MEMORY_VISIT_CHANCE = 0.35         # шанса патролата да оди на „омилено место“ на играчот
MEMORY_REMEMBER_THRESHOLD = 40.0   # над ова: на почетокот пишува „Се сеќаваат на тебе“

COLOR_MONSTER = (255, 60, 95)
COLOR_FLEE = (150, 150, 255)
COLOR_WAVE_DEATH = (255, 120, 60)
COLOR_WAVE_MONSTER = (200, 40, 60)
COLOR_WAVE_SHRIEK = (255, 70, 190)
COLOR_DEBUG_PATH = (255, 80, 80)
COLOR_DEBUG_SOUND_MEMORY = (255, 200, 0)
COLOR_DEBUG_DIRECTOR = (190, 150, 255)
COLOR_DEBUG_HEAT = (255, 140, 40)

# --- Аудио ---
AUDIO_MASTER_VOLUME = 0.8
AUDIO_PAN_WIDTH = 500              # на колку пиксели лево/десно звукот е целосно во едниот звучник
AUDIO_WALL_DAMPING = 0.45          # секој ѕид ја множи гласноста со ова
AUDIO_HEARTBEAT_DISTANCE = 260     # под ова растојание до чудовиште се слуша срцето

# --- Game loop ---
MAX_DT = 0.05  # горна граница за dt, за играта да не „скокне“ после замрзнување
