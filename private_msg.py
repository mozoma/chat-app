# private_msg.py Seif Mohamed — Message Protocol + Private Messages
# ============================================================
# Packet helpers and private message routing  Seif Mohamed
# ============================================================

import json
from datetime import datetime
from config import (
    T_PRIVATE, T_CHAT, T_SYSTEM, T_ERROR,
    T_FILE, T_IMAGE, T_VOICE, T_FILE_META,
    T_USER_LIST, T_ROOM_LIST, T_HISTORY,
    T_PONG, T_LOGIN
)


# ══════════════════════════════════════════════════════════════
#  Low-level packet helpers
# ══════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now().strftime("%H:%M")


def encode(data: dict) -> bytes:
    """Encode dict to bytes with newline."""
    return (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")


def decode(raw: str) -> dict:
    """Parse JSON string."""
    try:
        return json.loads(raw.strip())
    except Exception:
        return {}


# ── Specific builders ─────────────────────────────────────────

def pkt_chat(username: str, room: str, message: str) -> bytes:
    """Plain chat message packet."""
    return encode({"type": T_CHAT, "username": username,
                   "room": room, "content": message, "timestamp": _now()})


def pkt_system(message: str, room: str = "") -> bytes:
    """System message packet."""
    return encode({"type": T_SYSTEM, "content": message, "room": room})


def pkt_private(sender: str, receiver: str, content: str,
                msg_type: str = T_CHAT,
                filename: str = None, filesize: int = None,
                b64data: str = None) -> bytes:
    """Private message packet (text or file)."""
    d = {"type": T_PRIVATE, "sender": sender, "receiver": receiver,
         "msg_type": msg_type, "content": content, "timestamp": _now()}
    if filename:  d["filename"] = filename
    if filesize:  d["filesize"] = filesize
    if b64data:   d["data"]     = b64data
    return encode(d)


def pkt_file_meta(sender: str, target: str, filename: str,
                  filesize: int, is_private: bool = False) -> bytes:
    """Send file metadata before the actual data."""
    return encode({"type": T_FILE_META, "sender": sender, "target": target,
                   "filename": filename, "filesize": filesize,
                   "private": is_private, "timestamp": _now()})


def pkt_file(sender: str, target: str, filename: str,
             filesize: int, b64data: str,
             is_image: bool = False, is_private: bool = False) -> bytes:
    """Full file/image packet (base64)."""
    t = T_IMAGE if is_image else T_FILE
    return encode({"type": t, "sender": sender, "target": target,
                   "filename": filename, "filesize": filesize,
                   "data": b64data, "private": is_private, "timestamp": _now()})


def pkt_voice(sender: str, target: str, duration: float,
              b64data: str, is_private: bool = False) -> bytes:
    """Voice message packet."""
    return encode({"type": T_VOICE, "sender": sender, "target": target,
                   "duration": duration, "data": b64data,
                   "private": is_private, "timestamp": _now()})


def pkt_user_list(users: list) -> bytes:
    return encode({"type": T_USER_LIST, "users": users})


def pkt_room_list(rooms: list) -> bytes:
    return encode({"type": T_ROOM_LIST, "rooms": rooms})


def pkt_history(room: str, messages: list) -> bytes:
    return encode({"type": T_HISTORY, "room": room, "messages": messages})


def pkt_error(msg: str) -> bytes:
    return encode({"type": T_ERROR, "content": msg})


def pkt_pong() -> bytes:
    return encode({"type": T_PONG})


# ══════════════════════════════════════════════════════════════
#  Server-side private message handler
# ══════════════════════════════════════════════════════════════

class PrivateMessageHandler:
    """
    Routes private messages between users on the server.
    """

    def __init__(self, room_manager, database):
        self.rm  = room_manager
        self.db  = database

    def route(self, sender_sock, packet: dict) -> bool:
        """
        Route a private packet (text or file) to the receiver.

        Returns True on success.
        """
        sender   = packet.get("sender", "")
        receiver = packet.get("receiver", "")
        content  = packet.get("content", "")
        msg_type = packet.get("msg_type", T_CHAT)
        filename = packet.get("filename")
        filesize = packet.get("filesize")

        recv_sock = self.rm.socket_for(receiver)
        if recv_sock is None:
            try:
                sender_sock.send(pkt_error(f"'{receiver}' is not online."))
            except Exception:
                pass
            return False

        raw = encode(packet)

        # Send to receiver
        try:
            recv_sock.send(raw)
        except Exception:
            try:
                sender_sock.send(pkt_error(f"Could not deliver to '{receiver}'."))
            except Exception:
                pass
            return False

        # Echo to sender
        try:
            sender_sock.send(raw)
        except Exception:
            pass

        # Save to database
        try:
            self.db.save_private(sender, receiver, content,
                                 msg_type, filename, filesize)
        except Exception as e:
            print(f"[DB] private save error: {e}")

        return True