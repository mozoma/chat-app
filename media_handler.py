# media_handler.py → Mohamed Hazem
# ============================================================
# Centralized Media Handler
# Ties together file_transfer, voice_msg, and image utilities
# ============================================================

import os
import base64
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from config import (
    IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, MEDIA_DIR, VOICE_DIR,
    MAX_FILE_SIZE_MB, C
)
from file_transfer import (
    encode_file, decode_and_save, is_image,
    make_thumbnail_b64, b64_to_photoimage,
    human_size, file_icon, save_to_uploads
)
from voice_msg import (
    VoiceRecorder, VoicePlayer, get_wav_duration,
    format_duration, PYAUDIO_OK
)


# ══════════════════════════════════════════════════════════════
#  MediaHandler  — used by the client / GUI
# ══════════════════════════════════════════════════════════════

class MediaHandler:
    """
    Unified interface for all media types.
    """

    def __init__(self):
        self.recorder = VoiceRecorder()
        self.player   = VoicePlayer()

    # ── File picking ─────────────────────────────────────────

    def pick_file(self) -> str | None:
        """
        Open a file picker dialog.

        Returns:
            Path of selected file, or None.
        """
        path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("All Files", "*.*")]
        )
        return path if path else None

    def pick_image(self) -> str | None:
        """
        Open an image picker dialog.
        """
        ext_str = " ".join(f"*{e}" for e in IMAGE_EXTENSIONS)
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Images", ext_str), ("All Files", "*.*")]
        )
        return path if path else None

    # ── Encode helpers ───────────────────────────────────────

    def prepare_file(self, filepath: str) -> dict | None:
        """
        Prepare a file for sending (base64 encode).

        Returns dict with keys: filename, filesize, data, is_image
        Returns None on error.
        """
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("Error", "File not found.")
            return None

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            messagebox.showerror(
                "File Too Large",
                f"Max allowed size is {MAX_FILE_SIZE_MB} MB."
            )
            return None

        try:
            b64data, size = encode_file(filepath)
        except Exception as e:
            messagebox.showerror("Encode Error", str(e))
            return None

        filename = os.path.basename(filepath)
        return {
            "filename": filename,
            "filesize": size,
            "data":     b64data,
            "is_image": is_image(filename),
            "icon":     file_icon(filename),
            "human_size": human_size(size)
        }

    def prepare_voice(self, filepath: str, duration: float) -> dict | None:
        """
        Prepare a voice message for sending.
        """
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            b64data, size = encode_file(filepath)
        except Exception:
            return None
        return {
            "filename": os.path.basename(filepath),
            "filesize": size,
            "duration": duration,
            "data":     b64data
        }

    # ── Save received media ───────────────────────────────────

    def save_received_file(self, b64data: str, filename: str,
                           dest_dir: str = None) -> str:
        """
        Save a received file to disk.
        """
        d = dest_dir or MEDIA_DIR
        return decode_and_save(b64data, filename, dest_dir=d)

    def save_received_voice(self, b64data: str, filename: str = None) -> str:
        """
        Save a received voice message.
        """
        fname = filename or "voice_received.wav"
        return decode_and_save(b64data, fname, dest_dir=VOICE_DIR)

    # ── Thumbnails ───────────────────────────────────────────

    def get_thumbnail(self, filepath: str):
        """
        Return a thumbnail PhotoImage from an image file.
        """
        b64 = make_thumbnail_b64(filepath)
        if b64:
            return b64_to_photoimage(b64)
        return None

    def b64_thumbnail(self, b64data: str):
        """
        Return thumbnail PhotoImage from base64 image data.
        """
        # Save temp file then generate thumbnail
        try:
            tmp = os.path.join(MEDIA_DIR, "_tmp_thumb.png")
            raw = base64.b64decode(b64data)
            with open(tmp, "wb") as f:
                f.write(raw)
            return self.get_thumbnail(tmp)
        except Exception:
            return None

    # ── Voice recording ──────────────────────────────────────

    def start_recording(self) -> bool:
        """Start voice recording."""
        return self.recorder.start()

    def stop_recording(self) -> tuple[str, float]:
        """
        Stop recording. Returns (filepath, duration).
        """
        return self.recorder.stop()

    def recording_duration(self) -> float:
        """Current recording duration."""
        return self.recorder.get_duration()

    # ── Voice playback ───────────────────────────────────────

    def play_voice_file(self, filepath: str, on_done=None):
        """Play a voice file."""
        self.player.play_file(filepath, on_done)

    def play_voice_b64(self, b64data: str, on_done=None):
        """Play a voice message from base64."""
        self.player.play_b64(b64data, on_done)

    def stop_playback(self):
        """Stop playback."""
        self.player.stop()

    def is_playing(self) -> bool:
        return self.player.is_playing()

    # ── Image viewer ─────────────────────────────────────────

    def show_fullsize_image(self, filepath: str = None, b64data: str = None):
        """
        Open a popup window showing full-size image.
        """
        try:
            from PIL import Image, ImageTk
            import tkinter as tk

            if filepath:
                img = Image.open(filepath)
            elif b64data:
                import io
                raw = base64.b64decode(b64data)
                img = Image.open(io.BytesIO(raw))
            else:
                return

            # Downscale if very large
            max_w, max_h = 900, 700
            img.thumbnail((max_w, max_h), Image.LANCZOS)

            win = tk.Toplevel()
            win.title("Image Viewer")
            win.configure(bg=C["bg"])
            photo = ImageTk.PhotoImage(img)
            lbl   = tk.Label(win, image=photo, bg=C["bg"])
            lbl.image = photo  # prevent GC
            lbl.pack(padx=10, pady=10)
            win.lift()

        except ImportError:
            messagebox.showinfo("Image", "Install Pillow to view images.")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}")

    # ── Download helper ──────────────────────────────────────

    def download_file(self, b64data: str, filename: str) -> str | None:
        """
        Ask user for save location and save the file.

        Returns saved path or None.
        """
        save_path = filedialog.asksaveasfilename(
            initialfile=filename,
            title="Save File As"
        )
        if not save_path:
            return None
        try:
            raw = base64.b64decode(b64data)
            with open(save_path, "wb") as f:
                f.write(raw)
            messagebox.showinfo("Saved", f"File saved:\n{save_path}")
            return save_path
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            return None