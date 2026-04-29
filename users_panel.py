# ============================================================
# Online Users + Rooms Panel — WhatsApp style
# ============================================================

import customtkinter as ctk
from config import C


# ── Avatar helper ────────────────────────────────────────────

def _initials(name: str) -> str:
    """First 1–2 chars of name."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper() if name else "?"


AVATAR_COLORS = [
    "#25d366", "#128c7e", "#075e54",
    "#34b7f1", "#e9a500", "#9c27b0",
    "#f15c6d", "#00bcd4"
]

def _avatar_color(name: str) -> str:
    idx = sum(ord(c) for c in name) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]


# ══════════════════════════════════════════════════════════════
#  Left panel — combines search + users + rooms
# ══════════════════════════════════════════════════════════════

class SidePanel(ctk.CTkFrame):
    """
    Left panel: search + users + rooms.
    """

    def __init__(self, parent, my_username: str = "",
                 on_user_click=None, on_room_click=None,
                 on_create_room=None):
        """
        Args:
            on_user_click(username)  — open private chat
            on_room_click(room)      — switch room
            on_create_room()         — create a new room
        """
        super().__init__(parent, fg_color=C["panel"],
                         corner_radius=0, width=280)
        self.my_username   = my_username
        self.on_user_click = on_user_click
        self.on_room_click = on_room_click
        self.on_create_room = on_create_room
        self._active_room  = ""

        self.pack_propagate(False)
        self._build()

    # ─── Build ───────────────────────────────────────────────

    def _build(self):
        # ── Header ──────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["header"],
                           corner_radius=0, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Self avatar
        av = ctk.CTkLabel(
            hdr,
            text=_initials(self.my_username),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
            fg_color=_avatar_color(self.my_username),
            width=36, height=36, corner_radius=18
        )
        av.pack(side="left", padx=12, pady=10)

        ctk.CTkLabel(
            hdr, text=self.my_username,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["txt_primary"]
        ).pack(side="left")

        # ── Search bar ──────────────────────────────────────
        search_wrap = ctk.CTkFrame(self, fg_color=C["header"],
                                   corner_radius=0)
        search_wrap.pack(fill="x")
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        self.entry_search = ctk.CTkEntry(
            search_wrap,
            placeholder_text="🔍  Search or start new chat",
            textvariable=self.search_var,
            height=36, corner_radius=18,
            font=ctk.CTkFont(size=12),
            fg_color=C["input_bg"],
            border_color=C["divider"],
            text_color=C["txt_primary"],
            placeholder_text_color=C["txt_muted"]
        )
        self.entry_search.pack(fill="x", padx=10, pady=8)

        # ── Tab bar (Users | Rooms) ──────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color=C["header"],
                               corner_radius=0, height=36)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        self.tab_users = ctk.CTkButton(
            tab_bar, text="Users",
            width=120, height=32, corner_radius=0,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=C["green"], hover_color=C["green_dark"],
            command=lambda: self._show_tab("users")
        )
        self.tab_users.pack(side="left", expand=True, fill="x")

        self.tab_rooms = ctk.CTkButton(
            tab_bar, text="Rooms",
            width=120, height=32, corner_radius=0,
            font=ctk.CTkFont(size=12),
            fg_color=C["header"], hover_color=C["hover"],
            text_color=C["txt_secondary"],
            command=lambda: self._show_tab("rooms")
        )
        self.tab_rooms.pack(side="left", expand=True, fill="x")

        # ── Divider ──────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=C["divider"],
                     corner_radius=0).pack(fill="x")

        # ── Scrollable list ──────────────────────────────────
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=C["panel"],
            scrollbar_button_color=C["divider"],
            scrollbar_button_hover_color=C["green"]
        )
        self.list_frame.pack(fill="both", expand=True)

        # ── Rooms: bottom create button ──────────────────────
        self.btn_create_room = ctk.CTkButton(
            self, text="+ New Room",
            height=38, corner_radius=0,
            font=ctk.CTkFont(size=12),
            fg_color=C["header"], hover_color=C["hover"],
            text_color=C["green"],
            border_width=1, border_color=C["divider"],
            command=self.on_create_room
        )
        # Hidden until rooms tab is selected
        self._current_tab = "users"
        self._all_users: list = []
        self._all_rooms: list = []

    # ─── Tab switching ───────────────────────────────────────

    def _show_tab(self, tab: str):
        self._current_tab = tab
        if tab == "users":
            self.tab_users.configure(
                fg_color=C["green"], font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            self.tab_rooms.configure(
                fg_color=C["header"], font=ctk.CTkFont(size=12),
                text_color=C["txt_secondary"]
            )
            self.btn_create_room.pack_forget()
            self._render_users(self._all_users)
        else:
            self.tab_rooms.configure(
                fg_color=C["green"], font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            )
            self.tab_users.configure(
                fg_color=C["header"], font=ctk.CTkFont(size=12),
                text_color=C["txt_secondary"]
            )
            self.btn_create_room.pack(fill="x", side="bottom")
            self._render_rooms(self._all_rooms)

    def _on_search(self, *_):
        q = self.search_var.get().lower()
        if self._current_tab == "users":
            filtered = [u for u in self._all_users if q in u.lower()]
            self._render_users(filtered)
        else:
            filtered = [r for r in self._all_rooms if q in r.lower()]
            self._render_rooms(filtered)

    # ─── Update from server data ─────────────────────────────

    def update_users(self, users: list):
        """Update user list."""
        self._all_users = sorted(
            users,
            key=lambda u: (u != self.my_username, u.lower())
        )
        if self._current_tab == "users":
            self._render_users(self._all_users)

    def update_rooms(self, rooms: list):
        """Update room list."""
        self._all_rooms = rooms
        if self._current_tab == "rooms":
            self._render_rooms(rooms)

    def set_active_room(self, room: str):
        self._active_room = room
        if self._current_tab == "rooms":
            self._render_rooms(self._all_rooms)

    # ─── Render helpers ──────────────────────────────────────

    def _clear(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

    def _render_users(self, users: list):
        self._clear()
        if not users:
            ctk.CTkLabel(
                self.list_frame, text="No users online",
                font=ctk.CTkFont(size=12),
                text_color=C["txt_muted"]
            ).pack(pady=20)
            return

        for u in users:
            self._user_row(u)

    def _render_rooms(self, rooms: list):
        self._clear()
        for r in rooms:
            self._room_row(r)

    def _user_row(self, username: str):
        is_me  = username == self.my_username
        row = ctk.CTkFrame(
            self.list_frame, fg_color="transparent",
            height=62, corner_radius=0
        )
        row.pack(fill="x")
        row.pack_propagate(False)

        # Hover effect
        def _enter(e): row.configure(fg_color=C["hover"])
        def _leave(e): row.configure(fg_color="transparent")
        row.bind("<Enter>", _enter)
        row.bind("<Leave>", _leave)

        # Separator
        ctk.CTkFrame(row, height=1, fg_color=C["divider"],
                     corner_radius=0).place(relx=0, rely=1.0,
                                            anchor="sw", relwidth=1)

        # Avatar
        color = _avatar_color(username)
        av = ctk.CTkLabel(
            row, text=_initials(username),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white", fg_color=color,
            width=42, height=42, corner_radius=21
        )
        av.place(x=10, y=10)

        # Online dot
        ctk.CTkLabel(
            row, text="●",
            font=ctk.CTkFont(size=9),
            text_color=C["online"],
            fg_color=color,
            width=12, height=12, corner_radius=6
        ).place(x=40, y=38)

        # Name
        disp = f"{username}  (you)" if is_me else username
        ctk.CTkLabel(
            row, text=disp,
            font=ctk.CTkFont(size=13, weight="bold" if is_me else "normal"),
            text_color=C["txt_primary"],
            anchor="w"
        ).place(x=62, y=14)

        ctk.CTkLabel(
            row, text="Online",
            font=ctk.CTkFont(size=11),
            text_color=C["txt_secondary"],
            anchor="w"
        ).place(x=62, y=34)

        # PM button (hidden until hover)
        if not is_me and self.on_user_click:
            btn_pm = ctk.CTkButton(
                row, text="💬",
                width=30, height=26,
                corner_radius=8,
                font=ctk.CTkFont(size=12),
                fg_color=C["green"],
                hover_color=C["green_dark"],
                command=lambda u=username: self.on_user_click(u)
            )

            def _enter2(e, btn=btn_pm, r=row):
                r.configure(fg_color=C["hover"])
                btn.place(x=238, y=18)
            def _leave2(e, btn=btn_pm, r=row):
                r.configure(fg_color="transparent")
                btn.place_forget()

            row.bind("<Enter>", _enter2)
            row.bind("<Leave>", _leave2)
            for child in [av]:
                child.bind("<Enter>", _enter2)
                child.bind("<Leave>", _leave2)

        # Click whole row
        def _click(e, u=username):
            if u != self.my_username and self.on_user_click:
                self.on_user_click(u)
        row.bind("<Button-1>", _click)

    def _room_row(self, room: str):
        is_active = room == self._active_room
        bg = C["hover"] if is_active else "transparent"

        row = ctk.CTkFrame(
            self.list_frame, fg_color=bg,
            height=62, corner_radius=0
        )
        row.pack(fill="x")
        row.pack_propagate(False)

        def _enter(e): row.configure(fg_color=C["hover"])
        def _leave(e): row.configure(fg_color=bg)
        row.bind("<Enter>", _enter)
        row.bind("<Leave>", _leave)

        ctk.CTkFrame(row, height=1, fg_color=C["divider"],
                     corner_radius=0).place(relx=0, rely=1.0,
                                            anchor="sw", relwidth=1)

        # Room icon
        ctk.CTkLabel(
            row, text="#",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["green"],
            fg_color=C["input_bg"],
            width=42, height=42, corner_radius=21
        ).place(x=10, y=10)

        ctk.CTkLabel(
            row, text=room,
            font=ctk.CTkFont(size=13, weight="bold" if is_active else "normal"),
            text_color=C["txt_primary" if is_active else "txt_secondary"],
            anchor="w"
        ).place(x=62, y=14)

        ctk.CTkLabel(
            row, text="Tap to open",
            font=ctk.CTkFont(size=11),
            text_color=C["txt_muted"],
            anchor="w"
        ).place(x=62, y=34)

        if is_active:
            ctk.CTkLabel(
                row, text="●",
                font=ctk.CTkFont(size=10),
                text_color=C["green"]
            ).place(x=258, y=26)

        row.bind("<Button-1>",
                 lambda e, r=room: self.on_room_click and self.on_room_click(r))
