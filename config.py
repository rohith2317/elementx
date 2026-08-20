"""
config.py
Central configuration for ELEMENTX: AI Gesture Battle.
All tunable constants live here so gameplay/vision can be adjusted
without touching game logic.
"""

# ---------------------------------------------------------------------------
# WINDOW / DISPLAY
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "ELEMENTX: AI Gesture Battle"

# Webcam preview panel (drawn inside the pygame window)
CAM_PREVIEW_WIDTH = 240
CAM_PREVIEW_HEIGHT = 180
CAM_PREVIEW_POS = (20, SCREEN_HEIGHT - CAM_PREVIEW_HEIGHT - 20)  # bottom-left

# ---------------------------------------------------------------------------
# CAMERA / VISION
# ---------------------------------------------------------------------------
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS_TARGET = 30

GESTURE_COOLDOWN = 0.45          # seconds between repeated gesture triggers
GESTURE_CONFIDENCE_THRESHOLD = 0.6
GESTURE_SMOOTHING_FRAMES = 4      # majority vote over N frames to debounce

MAX_HANDS = 2

# ---------------------------------------------------------------------------
# COLORS (R, G, B)
# ---------------------------------------------------------------------------
COLOR_BG = (10, 12, 24)
COLOR_WHITE = (240, 240, 245)
COLOR_BLACK = (0, 0, 0)
COLOR_HP = (220, 40, 60)
COLOR_HP_BG = (60, 15, 20)
COLOR_ENERGY = (60, 160, 255)
COLOR_ENERGY_BG = (15, 35, 60)
COLOR_FIRE = (255, 120, 30)
COLOR_LIGHTNING = (255, 240, 90)
COLOR_WIND = (150, 255, 210)
COLOR_ENERGY_ATK = (170, 90, 255)
COLOR_SHIELD = (90, 200, 255)
COLOR_ULTIMATE = (255, 80, 200)
COLOR_UI_PANEL = (20, 22, 40, 180)
COLOR_ACCENT = (255, 200, 60)

# ---------------------------------------------------------------------------
# PLAYER
# ---------------------------------------------------------------------------
PLAYER_MAX_HP = 100
PLAYER_MAX_ENERGY = 100
PLAYER_ENERGY_REGEN_PER_SEC = 6
PLAYER_MOVE_SPEED = 6
PLAYER_START_POS = (260, 470)
PLAYER_SIZE = (90, 140)

# ---------------------------------------------------------------------------
# ABILITY ENERGY COSTS / DAMAGE
# ---------------------------------------------------------------------------
ABILITY_STATS = {
    "BASIC_PUNCH":   {"energy": 5,   "damage": 8,  "speed": 14, "color": COLOR_WHITE},
    "LIGHTNING":     {"energy": 15,  "damage": 18, "speed": 22, "color": COLOR_LIGHTNING},
    "WIND":          {"energy": 20,  "damage": 14, "speed": 10, "color": COLOR_WIND},
    "ENERGY_BLAST":  {"energy": 30,  "damage": 28, "speed": 16, "color": COLOR_ENERGY_ATK},
    "FIRE":          {"energy": 18,  "damage": 16, "speed": 12, "color": COLOR_FIRE},
    "ULTIMATE":      {"energy": 100, "damage": 60, "speed": 18, "color": COLOR_ULTIMATE},
    "SHIELD":        {"energy": 2,   "damage": 0,  "speed": 0,  "color": COLOR_SHIELD},
    "HEAL":          {"energy": 0,   "damage": 0,  "speed": 0,  "color": (90, 255, 140)},
}

# ---------------------------------------------------------------------------
# ENEMIES
# ---------------------------------------------------------------------------
ENEMY_STATS = {
    "TRAINING_BOT": {
        "hp": 60, "attack": 5, "attack_cd": 2.2, "speed": 1.5,
        "color": (150, 150, 160), "name": "Training Bot"
    },
    "SHADOW_BEAST": {
        "hp": 110, "attack": 9, "attack_cd": 1.6, "speed": 2.4,
        "color": (110, 60, 160), "name": "Shadow Beast"
    },
    "ELEMENT_GUARDIAN": {
        "hp": 170, "attack": 13, "attack_cd": 1.8, "speed": 1.8,
        "color": (60, 160, 140), "name": "Element Guardian", "ranged": True
    },
    "FINAL_BOSS": {
        "hp": 320, "attack": 16, "attack_cd": 1.2, "speed": 2.6,
        "color": (200, 40, 60), "name": "Voidrend, the Fallen Star",
        "ranged": True, "phases": 3, "can_dodge": True
    },
}

# ---------------------------------------------------------------------------
# ROUNDS (Wave-based progression)
# ---------------------------------------------------------------------------
# Each round has multiple enemies that spawn sequentially
ROUNDS = [
    {
        "id": 1,
        "name": "Training Arena",
        "enemy_count": 4,
        "enemy_type": "TRAINING_BOT",
        "difficulty_multiplier": 1.0,
        "bg": (26, 30, 46),
    },
    {
        "id": 2,
        "name": "Fire Arena",
        "enemy_count": 5,
        "enemy_type": "SHADOW_BEAST",
        "difficulty_multiplier": 1.25,
        "bg": (46, 22, 20),
    },
    {
        "id": 3,
        "name": "Storm Arena",
        "enemy_count": 6,
        "enemy_type": "SHADOW_BEAST",
        "difficulty_multiplier": 1.5,
        "bg": (20, 30, 46),
    },
    {
        "id": 4,
        "name": "Guardian's Sanctum",
        "enemy_count": 6,
        "enemy_type": "ELEMENT_GUARDIAN",
        "difficulty_multiplier": 1.8,
        "bg": (18, 38, 34),
    },
    {
        "id": 5,
        "name": "The Final Rift",
        "enemy_count": 3,
        "enemy_type": "FINAL_BOSS",
        "difficulty_multiplier": 2.2,
        "bg": (30, 12, 20),
    },
]

# Backward compatibility with old LEVELS config (deprecated)
LEVELS = ROUNDS

# ---------------------------------------------------------------------------
# UPGRADES
# ---------------------------------------------------------------------------
# Upgradeable player attributes
UPGRADE_OPTIONS = [
    {
        "name": "Max Health",
        "key": "max_health",
        "icon": "❤️",
        "description": "Increase maximum health",
        "base_value": 100,
        "per_upgrade": 15,
        "category": "defense",
    },
    {
        "name": "Attack Damage",
        "key": "attack_damage",
        "icon": "⚔️",
        "description": "Increase ability damage",
        "base_value": 1.0,  # multiplier
        "per_upgrade": 0.12,
        "category": "attack",
    },
    {
        "name": "Movement Speed",
        "key": "movement_speed",
        "icon": "💨",
        "description": "Increase movement speed",
        "base_value": 1.0,  # multiplier
        "per_upgrade": 0.1,
        "category": "mobility",
    },
    {
        "name": "Energy Regen",
        "key": "energy_regen",
        "icon": "⚡",
        "description": "Increase energy regeneration",
        "base_value": 6.0,
        "per_upgrade": 1.5,
        "category": "resource",
    },
    {
        "name": "Defense",
        "key": "defense",
        "icon": "🛡️",
        "description": "Reduce damage taken",
        "base_value": 1.0,  # multiplier
        "per_upgrade": 0.08,
        "category": "defense",
    },
]

# XP/Leveling
PLAYER_XP_PER_ENEMY = 25
PLAYER_XP_PER_ROUND_BONUS = 200
XP_TO_LEVEL = 100

# ---------------------------------------------------------------------------
# COMBO SYSTEM
# ---------------------------------------------------------------------------
COMBO_WINDOW_SECONDS = 2.5    # time allowed between hits to keep combo alive
COMBO_SCORE_MULTIPLIER = 10
COMBO_DAMAGE_BONUS_PER_STAGE = 0.03   # +3% damage per combo stage, capped
COMBO_DAMAGE_BONUS_CAP = 0.6

# Named gesture sequences -> special combo ability
GESTURE_COMBOS = {
    ("FIST", "ONE_FINGER", "TWO_FINGERS"): "ELEMENT_COMBO",
    ("ONE_FINGER", "THREE_FINGERS"): "LIGHTNING_BLAST_COMBO",
    ("OPEN_PALM", "FIST"): "SHIELD_COUNTER",
}
COMBO_SEQUENCE_WINDOW = 3.0    # seconds allowed to complete a combo sequence

# ---------------------------------------------------------------------------
# KEYBOARD FALLBACK
# ---------------------------------------------------------------------------
KEY_BINDINGS_HELP = {
    "A / D": "Move left / right",
    "J": "Basic Attack",
    "K": "Special Attack (Lightning)",
    "L": "Ultimate",
    "SPACE": "Shield",
    "ESC": "Pause",
}

# ---------------------------------------------------------------------------
# ASSET PATHS
# ---------------------------------------------------------------------------
ASSETS_DIR = "assets"
IMAGES_DIR = f"{ASSETS_DIR}/images"
SOUNDS_DIR = f"{ASSETS_DIR}/sounds"
FONTS_DIR = f"{ASSETS_DIR}/fonts"

SOUND_FILES = {
    "menu_music": f"{SOUNDS_DIR}/menu_music.ogg",
    "attack": f"{SOUNDS_DIR}/attack.wav",
    "lightning": f"{SOUNDS_DIR}/lightning.wav",
    "fire": f"{SOUNDS_DIR}/fire.wav",
    "wind": f"{SOUNDS_DIR}/wind.wav",
    "shield": f"{SOUNDS_DIR}/shield.wav",
    "hit": f"{SOUNDS_DIR}/hit.wav",
    "boss": f"{SOUNDS_DIR}/boss.wav",
    "victory": f"{SOUNDS_DIR}/victory.wav",
    "game_over": f"{SOUNDS_DIR}/game_over.wav",
    "ultimate": f"{SOUNDS_DIR}/ultimate.wav",
    "heal": f"{SOUNDS_DIR}/heal.wav",
}
