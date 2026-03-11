"""
Game settings and constants.

All tunable parameters live here so they're easy to find and adjust.
"""

# ── Display ──────────────────────────────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Storm the House"

# ── World layout (proportions of screen height) ─────────────────────────────
SKY_RATIO = 0.35          # top 35 % is sky
HORIZON_Y_RATIO = 0.35    # where sky meets ground
GROUND_RATIO = 0.65       # bottom 65 % is ground

# ── Colors ───────────────────────────────────────────────────────────────────
# Ground / sand
SAND_NEAR = (210, 180, 140)     # warm sand close to camera
SAND_FAR = (194, 168, 128)      # slightly darker at horizon
SAND_DARK = (180, 155, 115)     # shadow / variation tone

# House
HOUSE_WALL = (139, 90, 53)       # brown wall
HOUSE_WALL_LIGHT = (160, 110, 70)  # lit side
HOUSE_WALL_DARK = (110, 70, 40)   # shadowed side
HOUSE_ROOF = (100, 55, 30)       # darker brown roof
HOUSE_ROOF_EDGE = (80, 45, 25)
HOUSE_DOOR = (80, 45, 25)
HOUSE_WINDOW_FRAME = (90, 55, 30)
HOUSE_WINDOW_GLASS = (170, 210, 230)  # light blue glass
HOUSE_WINDOW_GLASS_SHINE = (210, 235, 250)
HOUSE_CHIMNEY = (95, 55, 30)

# Ambient
SHADOW_COLOR = (0, 0, 0, 40)     # translucent shadow
CLOUD_COLOR = (255, 255, 255)
CLOUD_SHADOW = (220, 225, 235)

# UI
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (40, 40, 40)

# ── House placement ──────────────────────────────────────────────────────────
HOUSE_RIGHT_MARGIN = 60          # px from right edge
HOUSE_WIDTH_RATIO = 0.18         # fraction of screen width
HOUSE_HEIGHT_RATIO = 0.52        # fraction of screen height

# ── Cloud settings ───────────────────────────────────────────────────────────
NUM_CLOUDS = 6
CLOUD_MIN_SPEED = 8
CLOUD_MAX_SPEED = 25
CLOUD_MIN_SCALE = 0.6
CLOUD_MAX_SCALE = 1.4

# ── Ground detail ────────────────────────────────────────────────────────────
NUM_GROUND_TUFTS = 35
NUM_GROUND_PEBBLES = 50
NUM_GROUND_DUST_PARTICLES = 12

# ── Enemy settings ──────────────────────────────────────────────────────────
ENEMY_SPAWN_INTERVAL = 3.0       # seconds between spawns
ENEMY_SPEED_MIN = 35             # px/s walk speed
ENEMY_SPEED_MAX = 55
ENEMY_STOP_DISTANCE = 80         # px before house left edge to stop
ENEMY_BASE_HEIGHT = 36           # base sprite height (scaled by depth)
ENEMY_WALK_FRAME_DURATION = 0.12 # seconds per walk animation frame
ENEMY_ATTACK_FRAME_DURATION = 0.18  # seconds per attack animation frame
ENEMY_ATTACK_COOLDOWN = 1.2      # seconds between shots
ENEMY_SPAWN_Y_MARGIN_TOP = 0.15  # fraction of ground area (from horizon)
ENEMY_SPAWN_Y_MARGIN_BOT = 0.10  # fraction of ground area (from bottom)

# Enemy colors
ENEMY_SKIN = (200, 160, 120)
ENEMY_SKIN_SHADOW = (170, 130, 95)
ENEMY_SHIRT = (75, 85, 70)          # olive / military green
ENEMY_SHIRT_SHADOW = (55, 65, 50)
ENEMY_PANTS = (65, 60, 55)          # dark grey-brown
ENEMY_PANTS_SHADOW = (45, 42, 38)
ENEMY_BOOTS = (40, 35, 30)
ENEMY_GUN_METAL = (60, 60, 65)
ENEMY_GUN_DARK = (40, 40, 45)
ENEMY_GUN_WOOD = (100, 65, 35)
ENEMY_HELMET = (85, 95, 80)
ENEMY_HELMET_SHADOW = (65, 75, 60)

# Muzzle flash
MUZZLE_FLASH_COLOR = (255, 240, 150)
MUZZLE_FLASH_BRIGHT = (255, 255, 220)
MUZZLE_FLASH_DURATION = 0.08        # seconds

# ── Player weapon ───────────────────────────────────────────────────────────
PLAYER_MAX_AMMO = 7
PLAYER_GUN_DAMAGE = 1
PLAYER_RELOAD_TIME = 5.0            # seconds

# ── Enemy HP ────────────────────────────────────────────────────────────────
ENEMY_HP = 3
ENEMY_DEATH_FADE_TIME = 0.4         # seconds to fade out on death

# ── Crosshair ──────────────────────────────────────────────────────────────
CROSSHAIR_SIZE = 20                 # outer radius in px
CROSSHAIR_GAP = 5                   # gap from center
CROSSHAIR_THICK = 2
CROSSHAIR_COLOR = (255, 255, 255)
CROSSHAIR_SHADOW = (0, 0, 0, 100)
CROSSHAIR_DOT = 2                   # center dot radius
RELOAD_ARC_RADIUS = 16
RELOAD_ARC_THICK = 3
RELOAD_ARC_BG = (255, 255, 255, 40)
RELOAD_ARC_FG = (255, 200, 60)

# ── Ammo HUD ───────────────────────────────────────────────────────────────
HUD_AMMO_X = 20
HUD_AMMO_Y = 30
HUD_BULLET_W = 6
HUD_BULLET_H = 18
HUD_BULLET_GAP = 5
HUD_BULLET_COLOR = (220, 190, 90)
HUD_BULLET_CASING = (180, 155, 60)
HUD_BULLET_EMPTY = (80, 75, 70)
HUD_BULLET_TIP = (200, 170, 80)
HUD_LABEL_COLOR = (230, 225, 215)

# ── House HP ───────────────────────────────────────────────────────────────
HOUSE_MAX_HP = 250
ENEMY_SHOT_DAMAGE = 10               # damage per enemy shot hitting the house

# ── House damage visuals ──────────────────────────────────────────────────
HOUSE_CRACK_COLOR = (50, 30, 15)
HOUSE_CRACK_SHADOW = (35, 20, 10, 120)
HOUSE_SCORCH_COLOR = (60, 45, 30, 80)

# ── House HP HUD (bottom-right) ──────────────────────────────────────────
HUD_HOUSE_HP_MARGIN = 20
HUD_HOUSE_HP_BAR_W = 180
HUD_HOUSE_HP_BAR_H = 14
HUD_HOUSE_HP_BG = (0, 0, 0, 130)
HUD_HOUSE_HP_BORDER = (160, 140, 110)
HUD_HOUSE_HP_FULL = (80, 180, 80)
HUD_HOUSE_HP_MID = (220, 180, 50)
HUD_HOUSE_HP_LOW = (200, 50, 40)
HUD_HOUSE_HP_EMPTY = (50, 45, 40)

# ── Money system ──────────────────────────────────────────────────────────
MONEY_START = 0
MONEY_PER_KILL = 10

# ── Money HUD (top-right) ────────────────────────────────────────────────
HUD_MONEY_MARGIN = 20
HUD_MONEY_COLOR = (100, 200, 80)
HUD_MONEY_SHADOW = (0, 0, 0)
HUD_MONEY_ICON_COLOR = (220, 200, 80)

# ── Day / time system ─────────────────────────────────────────────────────
DAY_DURATION = 60.0                  # seconds per day
DAY_END_BONUS = 100                  # money awarded at end of each day

# Sky color keyframes (keyed on time-of-day 0..1)
# Each entry: (t, top_color, horizon_color)
SKY_MORNING_TOP = (180, 210, 245)    # soft light blue
SKY_MORNING_HOR = (225, 215, 200)    # warm pale
SKY_NOON_TOP = (100, 165, 230)       # vibrant blue
SKY_NOON_HOR = (185, 215, 240)      # bright horizon
SKY_EVENING_TOP = (80, 100, 150)     # dusky blue
SKY_EVENING_HOR = (240, 170, 100)   # warm orange
SKY_SUNSET_TOP2 = (45, 55, 90)      # deep twilight
SKY_SUNSET_HOR2 = (220, 130, 70)    # deep orange

# Sun arc parameters
SUN_RADIUS = 32
SUN_ARC_LEFT_X = 0.05               # fraction of screen width at sunrise
SUN_ARC_RIGHT_X = 0.95              # fraction at sunset
SUN_ARC_PEAK_Y = 0.08               # fraction of screen height at noon
SUN_ARC_HORIZON_Y = 0.33            # fraction at sunrise/sunset (at horizon)

# ── Main menu ─────────────────────────────────────────────────────────────
MENU_TITLE_COLOR = (240, 230, 210)
MENU_SUBTITLE_COLOR = (200, 190, 170)
MENU_BTN_COLOR = (180, 140, 80)
MENU_BTN_HOVER = (220, 175, 100)
MENU_BTN_TEXT = (40, 30, 15)
MENU_BG_TOP = (45, 55, 90)
MENU_BG_BOT = (100, 75, 50)

# ── End-of-day screen ────────────────────────────────────────────────────
EOD_BG_ALPHA = 200
EOD_PANEL_COLOR = (30, 25, 20, EOD_BG_ALPHA)
EOD_TITLE_COLOR = (240, 220, 160)
EOD_STAT_LABEL = (180, 170, 155)
EOD_STAT_VALUE = (255, 245, 220)
EOD_BONUS_COLOR = (120, 210, 100)
EOD_BTN_COLOR = (160, 130, 70)
EOD_BTN_HOVER = (200, 165, 90)
EOD_BTN_TEXT = (40, 30, 15)

# ── Difficulty scaling ──────────────────────────────────────────────────
ENEMY_SPEED_SCALE_PER_DAY = 1.10     # enemies get 10 % faster each day
ENEMY_SPAWN_SCALE_PER_DAY = 0.85     # spawn interval shrinks by 15 % each day
ENEMY_SPAWN_VARIANCE = 1.0           # ±1 second random jitter on spawn timer
ENEMY_SPEED_VARIANCE = 0.10          # ±10 % random per-enemy speed modifier

# ── Upgrades ────────────────────────────────────────────────────────────
UPGRADE_BASE_COST = 100              # starting price for every upgrade
UPGRADE_PRICE_MULTIPLIER = 1.25      # price × this after each purchase
UPGRADE_DAMAGE_AMOUNT = 1            # +damage per level
UPGRADE_AMMO_AMOUNT = 1              # +max ammo per level
UPGRADE_RELOAD_FACTOR = 0.85         # reload_time × this per level (15 % faster)

# Repair House upgrade
REPAIR_BASE_COST = 100               # starting price for Repair House
REPAIR_PRICE_MULTIPLIER = 1.50       # cost increases by 50 % each purchase

# Fortify House upgrade (max 2 levels)
FORTIFY_MAX_LEVEL = 2
FORTIFY_COSTS = (250, 500)           # price for level 1, level 2
FORTIFY_HP_LEVELS = (500, 1000)      # max HP after each fortification level

# ── Hired Help ─────────────────────────────────────────────────────────
REPAIRMAN_COST = 150                 # flat cost per repairman (no scaling)
REPAIRMAN_HEAL_INTERVAL = 10.0       # seconds between heal ticks
REPAIRMAN_HEAL_PER_MAN = 1           # HP healed per repairman per tick
REPAIRMAN_MAX_VISIBLE = 10           # max repairmen drawn on/around house
REPAIRMAN_UNIQUE_SPOTS = 6           # first N have unique poses/positions

GUNMAN_COST = 150                    # flat cost per gunman (no scaling)
GUNMAN_BASE_INTERVAL = 10.0          # base seconds between shots
GUNMAN_SPEED_FACTOR = 0.90           # each extra gunman multiplies interval by this
GUNMAN_MAX_VISIBLE = 10              # max gunmen drawn on/around house
GUNMAN_UNIQUE_SPOTS = 6              # first N have unique poses/positions

# ── Debug controls ─────────────────────────────────────────────────────
DEBUG_MONEY_ADD = 1000               # money added per E press
TIME_SCALE_MIN = 0.25                # slowest game speed (T key)
TIME_SCALE_MAX = 10.0                # fastest game speed (R key)
TIME_SCALE_STEP = 2.0                # multiply / divide by this per press

# Upgrade card UI (end-of-day screen)
UPGRADE_CARD_W = 180
UPGRADE_CARD_H = 120
UPGRADE_CARD_GAP = 12
UPGRADE_CARD_BG = (40, 35, 28, 220)
UPGRADE_CARD_BORDER = (100, 90, 70)
UPGRADE_CARD_HOVER = (60, 52, 40, 230)
UPGRADE_CARD_LOCKED = (70, 60, 50, 100)   # when can't afford
UPGRADE_CARD_TITLE = (240, 225, 190)
UPGRADE_CARD_DESC = (180, 170, 150)
UPGRADE_CARD_PRICE = (120, 210, 100)
UPGRADE_CARD_PRICE_LOCKED = (180, 80, 60)
UPGRADE_CARD_LEVEL = (160, 150, 130)
UPGRADE_CARD_ICON = (220, 200, 120)

# ── Day HUD (top-center) ─────────────────────────────────────────────────
HUD_DAY_COLOR = (240, 230, 200)

# ── Blood particles ────────────────────────────────────────────────────────
BLOOD_COUNT_MIN = 5
BLOOD_COUNT_MAX = 10
BLOOD_SPEED_MIN = 30
BLOOD_SPEED_MAX = 120
BLOOD_LIFETIME_MIN = 0.3
BLOOD_LIFETIME_MAX = 0.8
BLOOD_GRAVITY = 250
BLOOD_COLORS = [
    (180, 30, 30),
    (160, 20, 20),
    (200, 40, 40),
    (140, 15, 15),
    (190, 50, 50),
]

# ── Dust particles (ground miss) ───────────────────────────────────────────
DUST_COUNT_MIN = 6
DUST_COUNT_MAX = 12
DUST_SPEED_MIN = 15
DUST_SPEED_MAX = 60
DUST_LIFETIME_MIN = 0.4
DUST_LIFETIME_MAX = 0.9
DUST_GRAVITY = 40
DUST_COLORS = [
    (200, 180, 145),
    (185, 165, 130),
    (215, 195, 155),
    (175, 155, 120),
]

# ── Explosion particles ───────────────────────────────────────────────────
EXPLOSION_COUNT_MIN = 25
EXPLOSION_COUNT_MAX = 40
EXPLOSION_SPEED_MIN = 80
EXPLOSION_SPEED_MAX = 250
EXPLOSION_LIFETIME_MIN = 0.5
EXPLOSION_LIFETIME_MAX = 1.2
EXPLOSION_GRAVITY = 150
EXPLOSION_COLORS = [
    (255, 200, 50),
    (255, 150, 30),
    (255, 100, 20),
    (255, 80, 10),
    (200, 80, 30),
    (150, 60, 20),
]

# ── Debris particles ───────────────────────────────────────────────────────
DEBRIS_COUNT_MIN = 12
DEBRIS_COUNT_MAX = 20
DEBRIS_SPEED_MIN = 60
DEBRIS_SPEED_MAX = 180
DEBRIS_LIFETIME_MIN = 0.6
DEBRIS_LIFETIME_MAX = 1.5
DEBRIS_GRAVITY = 300
DEBRIS_COLORS = [
    (80, 80, 85),
    (60, 60, 65),
    (100, 100, 105),
    (70, 70, 75),
    (50, 50, 55),
]

# ── Armored Car (boss enemy) ──────────────────────────────────────────────
ARMORED_CAR_HP = 10
ARMORED_CAR_SPEED = 120              # px/s when driving to position
ARMORED_CAR_ATTACK_COOLDOWN = 0.4    # 3x faster than grunt (1.2 / 3)
ARMORED_CAR_STOP_X_RATIO = 0.45     # Stop at 45% of screen width (middle)
ARMORED_CAR_MONEY_REWARD = 50       # 5x normal soldier reward

# Armored car colors (green military technical)
ARMORED_CAR_BODY = (85, 105, 70)         # olive green
ARMORED_CAR_BODY_DARK = (65, 80, 55)     # darker shadow
ARMORED_CAR_BODY_LIGHT = (110, 130, 90)  # highlight
ARMORED_CAR_WHEEL = (35, 35, 38)
ARMORED_CAR_WHEEL_RIM = (60, 60, 65)
ARMORED_CAR_GUN_MOUNT = (70, 80, 65)
ARMORED_CAR_GUN_BARREL = (50, 55, 58)
ARMORED_CAR_HEADLIGHT = (220, 220, 180)
ARMORED_CAR_TAILLIGHT = (180, 50, 40)

# Armored car damage visuals
ARMORED_CAR_CRACK_COLOR = (40, 35, 30)
ARMORED_CAR_CRACK_SHADOW = (25, 22, 18)
ARMORED_CAR_SMOKE_INTERVAL = 0.4
# Explosion settings
EXPLOSION_FLASH_DURATION = 0.15
EXPLOSION_SHAKE_DURATION = 0.3
EXPLOSION_SHAKE_INTENSITY = 8
