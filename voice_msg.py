# voice_msg.py → Mohamed Hazem
# ============================================================
# Voice Message Recording & Playback
# Uses pyaudio + wave. Falls back gracefully if unavailable.
# ============================================================

import os
import io
import wave
import base64
import threading
import time
from datetime import datetime
from config import VOICE_DIR, AUDIO_RATE, AUDIO_CHANNELS

# pyaudio is optional
try:
    import pyaudio
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False
    print("[voice_msg] pyaudio not installed — voice recording disabled.")


# ══════════════════════════════════════════════════════════════
#  Recorder
# ══════════════════════════════════════════════════════════════

class VoiceRecorder:
    """
    Records audio from microphone and saves as WAV.
    """

    def __init__(self):
        self._pa      = None
        self._stream  = None
        self._frames  = []
        self._recording = False
        self._start_time = 0.0
        self.last_file: str = None   # Path of last recorded file
        self.last_duration: float = 0.0

    # ── Public API ───────────────────────────────────────────

    def start(self) -> bool:
        """Start recording. Returns False if unavailable."""
        if not PYAUDIO_OK:
            return False
        if self._recording:
            return True
        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_RATE,
                input=True,
                frames_per_buffer=1024
            )
            self._frames    = []
            self._recording = True
            self._start_time = time.time()
            # Read in a separate thread
            threading.Thread(target=self._record_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"[VoiceRecorder] start error: {e}")
            self._cleanup()
            return False

    def stop(self) -> tuple[str, float]:
        """
        Stop recording and save to WAV file.

        Returns:
            (filepath, duration_seconds)
        """
        if not self._recording:
            return None, 0.0
        self._recording = False
        duration = time.time() - self._start_time
        time.sleep(0.1)  # Wait for thread to finish
        self._cleanup()

        if not self._frames:
            return None, 0.0

        # Save as WAV
        filename = datetime.now().strftime("voice_%Y%m%d_%H%M%S.wav")
        filepath = os.path.join(VOICE_DIR, filename)
        os.makedirs(VOICE_DIR, exist_ok=True)

        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(AUDIO_RATE)
            wf.writeframes(b"".join(self._frames))

        self.last_file     = filepath
        self.last_duration = duration
        self._frames = []
        return filepath, duration

    def get_duration(self) -> float:
        """Current recording duration in seconds."""
        if self._recording:
            return time.time() - self._start_time
        return 0.0

    # ── Internal ─────────────────────────────────────────────

    def _record_loop(self):
        """Audio read loop."""
        while self._recording:
            try:
                data = self._stream.read(1024, exception_on_overflow=False)
                self._frames.append(data)
            except Exception:
                break

    def _cleanup(self):
        """Clean up PyAudio resources."""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
        except Exception:
            pass
        try:
            if self._pa:
                self._pa.terminate()
        except Exception:
            pass
        self._stream = None
        self._pa     = None


# ══════════════════════════════════════════════════════════════
#  Player
# ══════════════════════════════════════════════════════════════

class VoicePlayer:
    """
    Plays WAV files using PyAudio or winsound as fallback.
    """

    def __init__(self):
        self._playing = False
        self._thread: threading.Thread = None

    def play_file(self, filepath: str, on_done=None):
        """
        Play an audio file in a background thread.

        Args:
            filepath: Path to WAV file
            on_done: Callback when playback finishes
        """
        if self._playing:
            self.stop()
        self._playing = True
        self._thread = threading.Thread(
            target=self._play_thread,
            args=(filepath, on_done),
            daemon=True
        )
        self._thread.start()

    def play_b64(self, b64data: str, on_done=None):
        """
        Play base64-encoded WAV data.
        """
        if not b64data:
            return
        raw = base64.b64decode(b64data)
        # Save temp file
        tmp = os.path.join(VOICE_DIR, "_tmp_play.wav")
        os.makedirs(VOICE_DIR, exist_ok=True)
        with open(tmp, "wb") as f:
            f.write(raw)
        self.play_file(tmp, on_done)

    def stop(self):
        """Stop playback."""
        self._playing = False

    def is_playing(self) -> bool:
        return self._playing

    def _play_thread(self, filepath: str, on_done):
        """Internal playback thread."""
        try:
            if PYAUDIO_OK:
                self._play_pyaudio(filepath)
            else:
                self._play_winsound(filepath)
        except Exception as e:
            print(f"[VoicePlayer] error: {e}")
        finally:
            self._playing = False
            if on_done:
                try:
                    on_done()
                except Exception:
                    pass

    def _play_pyaudio(self, filepath: str):
        """Play using PyAudio."""
        pa = pyaudio.PyAudio()
        try:
            with wave.open(filepath, "rb") as wf:
                stream = pa.open(
                    format=pa.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                chunk = 1024
                data  = wf.readframes(chunk)
                while data and self._playing:
                    stream.write(data)
                    data = wf.readframes(chunk)
                stream.stop_stream()
                stream.close()
        finally:
            pa.terminate()

    def _play_winsound(self, filepath: str):
        """Play using winsound (Windows built-in, no install needed)."""
        try:
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME)
        except ImportError:
            print("[VoicePlayer] No audio backend available (pyaudio or winsound needed).")
        except Exception as e:
            print(f"[VoicePlayer] winsound error: {e}")


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def get_wav_duration(filepath: str) -> float:
    """Get WAV file duration in seconds."""
    try:
        with wave.open(filepath, "rb") as wf:
            frames = wf.getnframes()
            rate   = wf.getframerate()
            return frames / rate
    except Exception:
        return 0.0


def format_duration(seconds: float) -> str:
    """Format time as MM:SS."""
    s = int(seconds)
    return f"{s // 60:01d}:{s % 60:02d}"