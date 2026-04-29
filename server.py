# server.py → Mohamed Hazem (Leader)
# ============================================================
# Main Server
# Multi-threaded server handling chat, files, voice, rooms
# ============================================================

import socket
import threading
import sys
import os
from datetime import datetime

from config import (
    SERVER_HOST, DEFAULT_PORT, MAX_CONNECTIONS, BUFFER_SIZE,
    DEFAULT_ROOMS, DEFAULT_ROOM, UPLOADS_DIR,
    T_CHAT, T_PRIVATE, T_FILE, T_IMAGE, T_VOICE,
    T_JOIN_ROOM, T_CREATE_ROOM, T_LOGIN, T_LOGOUT,
    T_USER_LIST, T_ROOM_LIST, T_HISTORY,
    T_SYSTEM, T_ERROR, T_PING, T_FILE_META
)
from database import Database
from rooms import RoomManager
from private_msg import (
    PrivateMessageHandler,
    pkt_chat, pkt_system, pkt_user_list, pkt_room_list,
    pkt_history, pkt_error, pkt_pong, encode, decode
)
from file_transfer import save_to_uploads


class ChatServer:
    """
    Main server managing all connections, rooms, and media.
    """

    def __init__(self, host: str = SERVER_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.db   = Database()
        self.rm   = RoomManager()
        self.pm   = PrivateMessageHandler(self.rm, self.db)
        self._clients_lock = threading.Lock()
        self._clients: list = []
        self.running = False
        self._server_sock = None

        # Seed default rooms in DB
        for r in DEFAULT_ROOMS:
            self.db.save_room(r, "System")

    # ─── Start / Stop ────────────────────────────────────────

    def start(self):
        """Start server."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(MAX_CONNECTIONS)
        self.running = True
        self._log(f" Server on {self.host}:{self.port}")

        try:
            while self.running:
                try:
                    sock, addr = self._server_sock.accept()
                    self._log(f"🔗 {addr}")
                    t = threading.Thread(
                        target=self._handle, args=(sock, addr), daemon=True
                    )
                    t.start()
                except OSError:
                    break
        except KeyboardInterrupt:
            self._log("Shutting down...")
        finally:
            self.stop()

    def stop(self):
        """Stop server."""
        self.running = False
        with self._clients_lock:
            for s in self._clients:
                try: s.close()
                except Exception: pass
            self._clients.clear()
        try: self._server_sock.close()
        except Exception: pass

    # ─── Per-client handler ──────────────────────────────────

    def _handle(self, sock, addr):
        """Handle a single client in its own thread."""
        username = None
        buf = ""
        with self._clients_lock:
            self._clients.append(sock)

        try:
            while self.running:
                try:
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        break
                    buf += data.decode("utf-8", errors="replace")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line:
                            pkt = decode(line)
                            username = self._process(sock, pkt, username)
                except ConnectionResetError:
                    break
                except Exception as e:
                    self._log(f"❌ {addr}: {e}")
                    break
        finally:
            self._disconnect(sock, username)

    def _process(self, sock, pkt: dict, username) -> str:
        """Process a single packet."""
        t = pkt.get("type", "")

        # ── LOGIN ────────────────────────────────────────────
        if t == T_LOGIN:
            username = (pkt.get("username") or "Anonymous").strip()[:32]
            self.rm.register(sock, username)
            self.db.upsert_user(username)
            self.rm.join_room(sock, DEFAULT_ROOM, username)
            # Send bootstrap data
            sock.send(pkt_room_list(self.rm.get_all_rooms()))
            sock.send(pkt_user_list(self.rm.get_all_usernames()))
            self._send_history(sock, DEFAULT_ROOM)
            self._bcast_all(pkt_user_list(self.rm.get_all_usernames()))
            self._bcast_room(DEFAULT_ROOM,
                             pkt_system(f" {username} joined!", DEFAULT_ROOM))
            self._log(f"👤 {username} connected")

        # ── PING ─────────────────────────────────────────────
        elif t == T_PING:
            try: sock.send(pkt_pong())
            except Exception: pass

        # ── CHAT ─────────────────────────────────────────────
        elif t == T_CHAT and username:
            room    = pkt.get("room", DEFAULT_ROOM)
            content = pkt.get("content", "").strip()
            if content:
                self.db.save_message(username, room, content)
                self._bcast_room(room, pkt_chat(username, room, content))
                self._log(f"[{room}] {username}: {content}")

        # ── PRIVATE ──────────────────────────────────────────
        elif t == T_PRIVATE and username:
            self.pm.route(sock, pkt)

        # ── FILE / IMAGE ─────────────────────────────────────
        elif t in (T_FILE, T_IMAGE) and username:
            self._handle_file(sock, pkt, username)

        # ── VOICE ────────────────────────────────────────────
        elif t == T_VOICE and username:
            self._handle_voice(sock, pkt, username)

        # ── JOIN ROOM ────────────────────────────────────────
        elif t == T_JOIN_ROOM and username:
            room = pkt.get("room", DEFAULT_ROOM)
            if not self.rm.room_exists(room):
                self.rm.create_room(room)
                self.db.save_room(room, username)
                self._bcast_all(pkt_room_list(self.rm.get_all_rooms()))

            old = self.rm.get_room(sock)
            self.rm.join_room(sock, room, username)

            if old != room:
                self._bcast_room(old, pkt_system(
                    f"🚪 {username} left.", old))
            self._send_history(sock, room)
            self._bcast_room(room, pkt_system(
                f"🚪 {username} joined #{room}.", room))

        # ── CREATE ROOM ──────────────────────────────────────
        elif t == T_CREATE_ROOM and username:
            room = (pkt.get("room") or "").strip()
            if room:
                if self.rm.create_room(room):
                    self.db.save_room(room, username)
                    self._bcast_all(pkt_room_list(self.rm.get_all_rooms()))
                else:
                    try:
                        sock.send(pkt_error(f"Room '{room}' already exists."))
                    except Exception:
                        pass

        return username

    # ─── File / Voice helpers ────────────────────────────────

    def _handle_file(self, sock, pkt: dict, username: str):
        """Save file to server and rebroadcast."""
        is_private = pkt.get("private", False)
        b64data    = pkt.get("data", "")
        filename   = pkt.get("filename", "file")
        t          = pkt.get("type")

        # Save server copy
        try:
            if b64data:
                save_to_uploads(b64data, filename)
        except Exception as e:
            self._log(f"[file save] {e}")

        # Log in DB
        sender = username
        room   = pkt.get("target", "")
        self.db.save_message(sender, room, f"[FILE:{filename}]",
                             msg_type=t, filename=filename,
                             filesize=pkt.get("filesize"))

        # Route
        if is_private:
            self.pm.route(sock, pkt)
        else:
            raw = encode(pkt)
            self._bcast_room(room, raw)

    def _handle_voice(self, sock, pkt: dict, username: str):
        """Route voice message."""
        is_private = pkt.get("private", False)
        room       = pkt.get("target", "")

        self.db.save_message(username, room, "[VOICE]",
                             msg_type="VOICE")
        if is_private:
            self.pm.route(sock, pkt)
        else:
            self._bcast_room(room, encode(pkt))

    # ─── Broadcast helpers ───────────────────────────────────

    def _bcast_room(self, room: str, data: bytes):
        """Broadcast to all members of a room."""
        for s in self.rm.get_room_sockets(room):
            try: s.send(data)
            except Exception: pass

    def _bcast_all(self, data: bytes):
        """Broadcast to all connected clients."""
        with self._clients_lock:
            socks = list(self._clients)
        for s in socks:
            try: s.send(data)
            except Exception: pass

    def _send_history(self, sock, room: str):
        """Send room history to a newly joined client."""
        history = self.db.get_room_history(room)
        try:
            sock.send(pkt_history(room, history))
        except Exception:
            pass

    # ─── Disconnect ──────────────────────────────────────────

    def _disconnect(self, sock, username: str):
        """Handle client disconnect."""
        room = self.rm.get_room(sock)
        self.rm.leave_all(sock)
        with self._clients_lock:
            if sock in self._clients:
                self._clients.remove(sock)
        try: sock.close()
        except Exception: pass

        if username:
            self._log(f"👋 {username} disconnected")
            self._bcast_room(room,
                pkt_system(f"🔴 {username} left.", room))
            self._bcast_all(pkt_user_list(self.rm.get_all_usernames()))

    # ─── Logging ─────────────────────────────────────────────

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")


# ─── Entry point ─────────────────────────────────────────────

if __name__ == "__main__":
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except ValueError: pass
    ChatServer(port=port).start()