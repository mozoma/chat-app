# config.py — Application Configuration
# ============================================================
# Developer: Full Team
# ============================================================

import os

# ==================== Network ====================
SERVER_HOST        = "0.0.0.0"
CLIENT_DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT       = 5555
MAX_CONNECTIONS    = 100
BUFFER_SIZE        = 8192          # Receive buffer size
CHUNK_SIZE         = 65536         # Chunk size for file transfer (64 KB)

# ==================== Reconnect ====================
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY        = 3         # Seconds between attempts

# ==================== Database ====================
DATABASE_FILE = "chat.db"

# ==================== Storage Directories ====================
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR     = os.path.join(BASE_DIR, "media")      # Received images/files
UPLOADS_DIR   = os.path.join(BASE_DIR, "uploads")    # Files on server
VOICE_DIR     = os.path.join(BASE_DIR, "voice")      # Voice messages

# Create dirs if not exist
for _d in (MEDIA_DIR, UPLOADS_DIR, VOICE_DIR):
    os.makedirs(_d, exist_ok=True)

# ==================== App ====================
APP_NAME     = "ChatApp"
LOGIN_WIDTH  = 460
LOGIN_HEIGHT = 580
MAIN_WIDTH   = 1100
MAIN_HEIGHT  = 700
PM_WIDTH     = 440
PM_HEIGHT    = 600

# ==================== WhatsApp Dark Palette ====================
C = {
    # Backgrounds
    "bg":          "#0b141a",    # Main chat background
    "panel":       "#111b21",    # Left panel
    "header":      "#202c33",    # Title bar
    "input_bg":    "#2a3942",    # Input fields
    "bubble_in":   "#202c33",    # Received bubble
    "bubble_out":  "#005c4b",    # Sent bubble
    "hover":       "#2a3942",    # Hover effect
    "divider":     "#222d34",    # Divider lines
    "modal":       "#233138",    # Modal windows
    # Text
    "txt_primary": "#e9edef",
    "txt_secondary":"#8696a0",
    "txt_muted":   "#4a5568",
    "txt_link":    "#53bdeb",
    # Accent
    "green":       "#00a884",    # Primary green
    "green_dark":  "#008a6d",
    "green_light": "#25d366",
    "red":         "#f15c6d",
    "blue":        "#53bdeb",
    "orange":      "#e9a500",
    "online":      "#25d366",
}

# ==================== Audio ====================
AUDIO_RATE     = 44100
AUDIO_CHANNELS = 1
AUDIO_FORMAT   = "wav"     # pyaudio format string

# ==================== File Limits ====================
MAX_FILE_SIZE_MB  = 100    # Maximum file size (MB)
IMAGE_THUMB_SIZE  = (200, 160)   # Thumbnail size
IMAGE_EXTENSIONS  = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
AUDIO_EXTENSIONS  = {".wav", ".mp3", ".ogg", ".m4a"}

# ==================== Message Types (Protocol) ====================
T_CHAT        = "CHAT"
T_PRIVATE     = "PRIVATE"
T_FILE        = "FILE"
T_FILE_CHUNK  = "FILE_CHUNK"
T_FILE_END    = "FILE_END"
T_IMAGE       = "IMAGE"
T_VOICE       = "VOICE"
T_SYSTEM      = "SYSTEM"
T_LOGIN       = "LOGIN"
T_LOGOUT      = "LOGOUT"
T_USER_LIST   = "USER_LIST"
T_ROOM_LIST   = "ROOM_LIST"
T_JOIN_ROOM   = "JOIN_ROOM"
T_CREATE_ROOM = "CREATE_ROOM"
T_HISTORY     = "HISTORY"
T_ERROR       = "ERROR"
T_PING        = "PING"
T_PONG        = "PONG"
T_FILE_META   = "FILE_META"   # Metadata sent before actual transfer

# ==================== Default Rooms ====================
DEFAULT_ROOMS = ["General", "Tech Talk", "Random"]
DEFAULT_ROOM  = "General"
