"""
config.py — Full configuration for NeuraAI_v200 Hardcode
Author: CHATGPT + Joshua•Dav
"""

# ----------------------------
# API Keys
# ----------------------------
OPENAI_API_KEY = "10746353"           # Replace with real key
HUGGINGFACE_API_KEY = "1056431"       # Replace with real key

# ----------------------------
# Voice Preferences
# ----------------------------
DEFAULT_VOICE_GENDER = "female"       # female / male
DEFAULT_PERSONA = "friendly"          # friendly / polite / tech_genius
ENABLE_VOICE = True                    # Enable voice engine

# ----------------------------
# Premium / Session Settings
# ----------------------------
PREMIUM_PRICE = 6.99                   # Monthly premium pass
FREE_SESSION_HOURS = 3                 # Free offline session
PREMIUM_SESSION_HOURS = 12             # Premium daily session duration

# ----------------------------
# Chat & Memory
# ----------------------------
MAX_CHAT_LOGS = 1000                   # Max entries in chat_logs.json
ENABLE_OFFLINE_MODE = True             # Allow offline fallback
MEMORY_STORE_FILE = "memory_store.json"
CHAT_LOGS_FILE = "chat_logs.json"

# ----------------------------
# Mini-Games / Automation
# ----------------------------
ENABLE_MINI_GAMES = True
ENABLE_AUTOMATION = True
AUTOMATION_PREMIUM_ONLY = True         # Limit full automation to premium

# ----------------------------
# UI / Frontend
# ----------------------------
DEFAULT_LANGUAGE = "English"
AVAILABLE_LANGUAGES = ["English", "French", "Spanish"]
DEFAULT_BACKGROUND = "neon-bg"
AVAILABLE_BACKGROUNDS = ["neon-bg", "dark-bg", "light-bg"]

# ----------------------------
# Miscellaneous
# ----------------------------
BOT_NAMES_MALE = ["Alex", "James", "Ethan", "Liam", "Noah", "Aiden", "Lucas", "Mason", "Logan", "Elijah"]
BOT_NAMES_FEMALE = ["Sophia", "Emma", "Olivia", "Ava", "Isabella", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn"]
MAX_EMOJIS = 500
UPDATE_INTERVAL_DAYS = 30              # Automatic tweaks / new features every 1 month
TEXT_RESPONSE_SPEED = 0.2              # Seconds
IMAGE_GENERATION_TIME = 90             # Seconds (1-2 minutes range)