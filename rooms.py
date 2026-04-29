# ============================================================
# Room Management
# ============================================================

import threading
from config import DEFAULT_ROOMS, DEFAULT_ROOM


class RoomManager:
    """
    Thread-safe chat room and membership manager.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # room_name → set of client sockets
        self._rooms: dict[str, set] = {r: set() for r in DEFAULT_ROOMS}
        # socket → current room
        self._client_room: dict = {}
        # socket → username
        self._client_user: dict = {}

    # ─── Rooms ───────────────────────────────────────────────

    def create_room(self, name: str) -> bool:
        """Create a new room. Returns False if already exists."""
        with self._lock:
            if name in self._rooms:
                return False
            self._rooms[name] = set()
            return True

    def room_exists(self, name: str) -> bool:
        """Check if a room exists."""
        with self._lock:
            return name in self._rooms

    def get_all_rooms(self) -> list:
        """Get a list of all room names."""
        with self._lock:
            return list(self._rooms.keys())

    def get_room_sockets(self, room: str) -> list:
        """Get list of sockets in a room."""
        with self._lock:
            return list(self._rooms.get(room, set()))

    def get_room_members(self, room: str) -> list:
        """Get usernames of all members in a room."""
        with self._lock:
            return [self._client_user.get(s, "?") for s in self._rooms.get(room, set())]

    def get_room_count(self, room: str) -> int:
        """Get the number of members in a room."""
        with self._lock:
            return len(self._rooms.get(room, set()))

    # ─── Membership ──────────────────────────────────────────

    def join_room(self, sock, room: str, username: str) -> bool:
        """Join a room, leaving the current one first."""
        with self._lock:
            if room not in self._rooms:
                self._rooms[room] = set()
            old = self._client_room.get(sock)
            if old and old in self._rooms:
                self._rooms[old].discard(sock)
            self._rooms[room].add(sock)
            self._client_room[sock] = room
            self._client_user[sock]  = username
            return True

    def register(self, sock, username: str):
        """Register a new client without joining a room."""
        with self._lock:
            self._client_user[sock] = username

    def leave_all(self, sock):
        """Remove a client from everything (on disconnect)."""
        with self._lock:
            room = self._client_room.pop(sock, None)
            if room and room in self._rooms:
                self._rooms[room].discard(sock)
            self._client_user.pop(sock, None)

    # ─── Lookups ─────────────────────────────────────────────

    def get_room(self, sock) -> str:
        with self._lock:
            return self._client_room.get(sock, DEFAULT_ROOM)

    def get_username(self, sock) -> str:
        with self._lock:
            return self._client_user.get(sock, "Unknown")

    def get_all_usernames(self) -> list:
        with self._lock:
            return list(set(self._client_user.values()))

    def get_all_sockets(self) -> list:
        with self._lock:
            return list(self._client_user.keys())

    def socket_for(self, username: str):
        """Find socket by username."""
        with self._lock:
            for s, u in self._client_user.items():
                if u == username:
                    return s
            return None
