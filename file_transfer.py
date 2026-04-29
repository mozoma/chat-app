# file_transfer.py →  
# ============================================================
# File & Image Transfer Logic
# Handles encoding, decoding, saving, and sending files
# ============================================================

import os
import base64
import hashlib
from pathlib import Path
from config import (
    UPLOADS_DIR, MEDIA_DIR, CHUNK_SIZE,
    MAX_FILE_SIZE_MB, IMAGE_EXTENSIONS, C
)


# ══════════════════════════════════════════════════════════════
#  Utility helpers
# ══════════════════════════════════════════════════════════════

def human_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable string.
    """
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def is_image(filename: str) -> bool:
    """Check if the file is an image."""
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def file_icon(filename: str) -> str:
    """Return a file icon based on extension."""
    ext = Path(filename).suffix.lower()
    icons = {
        ".pdf": "📄", ".doc": "📝", ".docx": "📝",
        ".xls": "📊", ".xlsx": "📊", ".ppt": "📑", ".pptx": "📑",
        ".zip": "🗜️", ".rar": "🗜️", ".7z": "🗜️",
        ".mp3": "🎵", ".wav": "🎵", ".ogg": "🎵",
        ".mp4": "🎬", ".avi": "🎬", ".mkv": "🎬",
        ".py": "🐍", ".js": "📜", ".html": "🌐",
        ".txt": "📃", ".csv": "📊",
    }
    return icons.get(ext, "📎")


# ══════════════════════════════════════════════════════════════
#  Encode / Decode
# ══════════════════════════════════════════════════════════════

def encode_file(filepath: str) -> tuple[str, int]:
    """
    Read and base64-encode a file.

    Returns:
        (b64_string, file_size_bytes)
    Raises:
        ValueError if file too large
        FileNotFoundError if missing
    """
    size = os.path.getsize(filepath)
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if size > max_bytes:
        raise ValueError(f"File too large ({human_size(size)}). Max {MAX_FILE_SIZE_MB} MB.")

    with open(filepath, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii"), size


def decode_and_save(b64data: str, filename: str,
                    dest_dir: str = None, is_voice: bool = False) -> str:
    """
    Decode base64 data and save file to disk.

    Returns:
        Absolute path of saved file
    """
    if dest_dir is None:
        dest_dir = MEDIA_DIR
    os.makedirs(dest_dir, exist_ok=True)

    # Avoid name collisions
    base = Path(filename).stem
    ext  = Path(filename).suffix
    safe_name = filename
    counter   = 1
    while os.path.exists(os.path.join(dest_dir, safe_name)):
        safe_name = f"{base}_{counter}{ext}"
        counter  += 1

    dest_path = os.path.join(dest_dir, safe_name)
    raw_bytes = base64.b64decode(b64data)
    with open(dest_path, "wb") as f:
        f.write(raw_bytes)
    return dest_path


# ══════════════════════════════════════════════════════════════
#  Server-side: save uploaded files
# ══════════════════════════════════════════════════════════════

def save_to_uploads(b64data: str, filename: str) -> str:
    """Save a file to the uploads directory on the server."""
    return decode_and_save(b64data, filename, dest_dir=UPLOADS_DIR)


# ══════════════════════════════════════════════════════════════
#  Image thumbnail (for chat preview)
# ══════════════════════════════════════════════════════════════

def make_thumbnail_b64(filepath: str,
                       size: tuple = (200, 160)) -> str | None:
    """
    Create a base64 thumbnail for chat preview.

    Returns None if Pillow not available or error.
    """
    try:
        from PIL import Image
        import io
        img = Image.open(filepath)
        img.thumbnail(size, Image.LANCZOS)
        buf = io.BytesIO()
        fmt = img.format or "PNG"
        if fmt.upper() not in ("JPEG", "PNG", "GIF", "WEBP"):
            fmt = "PNG"
        img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def b64_to_photoimage(b64str: str):
    """
    Convert base64 string to tkinter PhotoImage.

    Returns None on failure.
    """
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
        import io
        raw  = base64.b64decode(b64str)
        img  = Image.open(io.BytesIO(raw))
        return ImageTk.PhotoImage(img)
    except Exception:
        try:
            import tkinter as tk
            raw = base64.b64decode(b64str)
            return tk.PhotoImage(data=b64str)
        except Exception:
            return None