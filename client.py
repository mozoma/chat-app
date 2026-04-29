# client.py — Client Connection Logic
# ============================================================
# Manages server connection, sending all message types,
# auto-reconnect, and message dispatch callbacks.
# ============================================================
#            Seif Mohamed########

import socket
import threading
import time

from config import (
    BUFFER_SIZE, MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY,
    DEFAULT_ROOM, T_LOGIN, T_CHAT, T_PRIVATE,
    T_FILE, T_IMAGE, T_VOICE, T_JOIN_ROOM, T_CREATE_ROOM,
    T_USER_LIST, T_PING
)
from private_msg import (
    encode, decode,
    pkt_chat, pkt_private, pkt_file, pkt_voice,
    pkt_user_list, pkt_room_list
)


class ChatClient:
    """
    Main client managing server connection and providing API for GUI.
    """

    def __init__(self, host: str, port: int, username: str,
                 on_message=None, on_connect=None, on_disconnect=None):
        """
        Args:
            host: Server address
            port: Port number
            username: Username
            on_message: callback(packet: dict)
            on_connect: callback()
            on_disconnect: callback(reason: str)
        """
        self.host     = host
        self.port     = port
        self.username = username

        self.on_message    = on_message
        self.on_connect    = on_connect
        self.on_disconnect = on_disconnect

        self.sock      = None
        self.connected = False
        self.current_room = DEFAULT_ROOM
        self._stop     = threading.Event()
        self._reconnect_count = 0

    # ─── Connect / Disconnect ────────────────────────────────

    def connect(self) -> bool:
        """
        Connect to server and send LOGIN.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            self.connected = True
            self._stop.clear()
            self._reconnect_count = 0

            # Login
            self._send_raw(encode({
                "type": T_LOGIN, "username": self.username
            }))

            # Start listener
            threading.Thread(target=self._recv_loop, daemon=True).start()

            if self.on_connect:
                self.on_connect()
            return True

        except ConnectionRefusedError:
            self._notify_disconnect("❌ Connection refused. Is the server running?")
        except socket.timeout:
            self._notify_disconnect("❌ Connection timed out.")
        except Exception as e:
            self._notify_disconnect(f"❌ {e}")
        return False

    def disconnect(self):
        """Disconnect from server."""
        self.connected = False
        self._stop.set()
        if self.sock:
            try: self.sock.close()
            except Exception: pass
            self.sock = None

    def reconnect(self):
        """Auto-reconnect to server."""
        self.disconnect()
        while (self._reconnect_count < MAX_RECONNECT_ATTEMPTS
               and not self._stop.is_set()):
            self._reconnect_count += 1
            self._notify({"type": "SYSTEM",
                          "content": f"🔄 Reconnecting {self._reconnect_count}/{MAX_RECONNECT_ATTEMPTS}..."})
            time.sleep(RECONNECT_DELAY)
            if self.connect():
                self.join_room(self.current_room)
                return
        self._notify_disconnect("🔴 Server unreachable. Please reconnect manually.")

    # ─── Receive loop ────────────────────────────────────────

    def _recv_loop(self):
        """Receive loop."""
        buf = ""
        while self.connected and not self._stop.is_set():
            try:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                buf += data.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        pkt = decode(line)
                        if pkt:
                            self._notify(pkt)
            except OSError:
                break
            except Exception as e:
                if self.connected:
                    print(f"[client] recv error: {e}")
                break

        if self.connected and not self._stop.is_set():
            self.connected = False
            threading.Thread(target=self.reconnect, daemon=True).start()

    # ─── Send helpers ────────────────────────────────────────

    def _send_raw(self, data: bytes):
        """Send raw bytes."""
        if self.sock and self.connected:
            try:
                self.sock.sendall(data)
            except Exception as e:
                print(f"[client] send error: {e}")
                self.connected = False

    def send_message(self, message: str, room: str = None):
        """Send a text message."""
        r = room or self.current_room
        self._send_raw(pkt_chat(self.username, r, message))

    def send_private(self, receiver: str, content: str,
                     msg_type: str = "CHAT",
                     filename: str = None, filesize: int = None,
                     b64data: str = None):
        """Send a private message."""
        from private_msg import pkt_private
        self._send_raw(pkt_private(
            self.username, receiver, content,
            msg_type=msg_type,
            filename=filename, filesize=filesize,
            b64data=b64data
        ))

    def send_file(self, target: str, filename: str, filesize: int,
                  b64data: str, is_image: bool = False,
                  is_private: bool = False):
        """Send a file or image."""
        self._send_raw(pkt_file(
            self.username, target, filename, filesize, b64data,
            is_image=is_image, is_private=is_private
        ))

    def send_voice(self, target: str, duration: float,
                   b64data: str, is_private: bool = False):
        """Send a voice message."""
        self._send_raw(pkt_voice(
            self.username, target, duration, b64data,
            is_private=is_private
        ))

    def join_room(self, room: str):
        """Join a room."""
        self.current_room = room
        self._send_raw(encode({
            "type": T_JOIN_ROOM, "room": room
        }))

    def create_room(self, room: str):
        """Create a room."""
        self._send_raw(encode({
            "type": T_CREATE_ROOM, "room": room
        }))

    def ping(self):
        """Check connection."""
        self._send_raw(encode({"type": T_PING}))

    # ─── Callbacks ───────────────────────────────────────────

    def _notify(self, pkt: dict):
        if self.on_message:
            try:
                self.on_message(pkt)
            except Exception as e:
                print(f"[client] callback error: {e}")

    def _notify_disconnect(self, reason: str = ""):
        self.connected = False
        if reason:
            self._notify({"type": "SYSTEM", "content": reason})
        if self.on_disconnect:
            try:
                self.on_disconnect(reason)
            except Exception:
                pass