# database.py → mohamed hazem
# ============================================================
# Database - storing messages, files, and users
# ============================================================

import sqlite3
from datetime import datetime
from config import DATABASE_FILE


class Database:
    """
    Handles all SQLite database operations.
    """

    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self._create_tables()

    # ─── Connection helper ───────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Return a fresh connection."""
        c = sqlite3.connect(self.db_file, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    # ─── Schema ──────────────────────────────────────────────

    def _create_tables(self):
        """Create all tables."""
        conn = self._conn()
        cur = conn.cursor()

        # Room messages
        cur.execute("""CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT    NOT NULL,
            room      TEXT    NOT NULL DEFAULT 'General',
            msg_type  TEXT    NOT NULL DEFAULT 'CHAT',
            content   TEXT    NOT NULL,
            filename  TEXT,
            filesize  INTEGER,
            filepath  TEXT,
            timestamp TEXT    NOT NULL
        )""")

        # Private messages
        cur.execute("""CREATE TABLE IF NOT EXISTS private_messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sender    TEXT    NOT NULL,
            receiver  TEXT    NOT NULL,
            msg_type  TEXT    NOT NULL DEFAULT 'CHAT',
            content   TEXT    NOT NULL,
            filename  TEXT,
            filesize  INTEGER,
            filepath  TEXT,
            timestamp TEXT    NOT NULL
        )""")

        # Users
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    UNIQUE NOT NULL,
            first_seen TEXT    NOT NULL,
            last_seen  TEXT    NOT NULL
        )""")

        # Rooms
        cur.execute("""CREATE TABLE IF NOT EXISTS rooms (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    UNIQUE NOT NULL,
            created_by TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )""")

        conn.commit()
        conn.close()

    # ─── Public messages ─────────────────────────────────────

    def save_message(self, username: str, room: str, content: str,
                     msg_type: str = "CHAT", filename: str = None,
                     filesize: int = None, filepath: str = None) -> int:
        """Save a public message."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO messages
               (username,room,msg_type,content,filename,filesize,filepath,timestamp)
               VALUES (?,?,?,?,?,?,?,?)""",
            (username, room, msg_type, content, filename, filesize, filepath, ts)
        )
        mid = cur.lastrowid
        conn.commit(); conn.close()
        return mid

    def get_room_history(self, room: str, limit: int = 60) -> list:
        """Get room message history."""
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute(
            """SELECT * FROM messages WHERE room=?
               ORDER BY id DESC LIMIT ?""", (room, limit)
        )
        rows = [dict(r) for r in reversed(cur.fetchall())]
        conn.close()
        return rows

    # ─── Private messages ────────────────────────────────────

    def save_private(self, sender: str, receiver: str, content: str,
                     msg_type: str = "CHAT", filename: str = None,
                     filesize: int = None, filepath: str = None) -> int:
        """Save a private message."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO private_messages
               (sender,receiver,msg_type,content,filename,filesize,filepath,timestamp)
               VALUES (?,?,?,?,?,?,?,?)""",
            (sender, receiver, msg_type, content, filename, filesize, filepath, ts)
        )
        mid = cur.lastrowid
        conn.commit(); conn.close()
        return mid

    def get_private_history(self, u1: str, u2: str, limit: int = 60) -> list:
        """Get private chat history between two users."""
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute(
            """SELECT * FROM private_messages
               WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
               ORDER BY id DESC LIMIT ?""",
            (u1, u2, u2, u1, limit)
        )
        rows = [dict(r) for r in reversed(cur.fetchall())]
        conn.close()
        return rows

    # ─── Users ───────────────────────────────────────────────

    def upsert_user(self, username: str):
        """Insert or update a user record."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute(
            """INSERT INTO users (username,first_seen,last_seen) VALUES (?,?,?)
               ON CONFLICT(username) DO UPDATE SET last_seen=excluded.last_seen""",
            (username, now, now)
        )
        conn.commit(); conn.close()

    # ─── Rooms ───────────────────────────────────────────────

    def save_room(self, name: str, created_by: str):
        """Save a room."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO rooms (name,created_by,created_at) VALUES (?,?,?)",
                (name, created_by, now)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def get_all_rooms(self) -> list:
        """Get all rooms."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT name FROM rooms ORDER BY created_at"
        ).fetchall()
        conn.close()
        return [r["name"] for r in rows]