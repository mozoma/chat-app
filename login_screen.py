# login_screen.py → 
# ============================================================
# WhatsApp-themed Login Screen
# ============================================================

import customtkinter as ctk
from config import APP_NAME, LOGIN_WIDTH, LOGIN_HEIGHT, CLIENT_DEFAULT_HOST, DEFAULT_PORT, C


class LoginScreen(ctk.CTkToplevel):
    """
    WhatsApp dark-themed login window.
    """

    def __init__(self, on_connect):
        """
        Args:
            on_connect: callback(username, host, port)
        """
        super().__init__()
        self.on_connect = on_connect

        self.title(f"{APP_NAME}")
        self.geometry(f"{LOGIN_WIDTH}x{LOGIN_HEIGHT}")
        self.resizable(False, False)
        self.configure(fg_color=C["panel"])
        self._center()
        self._build()
        self.bind("<Return>", lambda e: self._do_connect())
        self.after(150, self.e_user.focus_set)

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - LOGIN_WIDTH)  // 2
        y = (self.winfo_screenheight() - LOGIN_HEIGHT) // 2
        self.geometry(f"{LOGIN_WIDTH}x{LOGIN_HEIGHT}+{x}+{y}")

    def _build(self):
        """Build UI."""
        # ── Top green bar ────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=C["green"], corner_radius=0, height=8)
        top.pack(fill="x")

        # ── Logo / Header ────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["header"], corner_radius=0)
        hdr.pack(fill="x")

        ctk.CTkLabel(hdr, text="💬", font=ctk.CTkFont(size=52)).pack(pady=(28, 4))
        ctk.CTkLabel(
            hdr, text=APP_NAME,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=C["green_light"]
        ).pack()
        ctk.CTkLabel(
            hdr, text="Connect to your chat server",
            font=ctk.CTkFont(size=12), text_color=C["txt_secondary"]
        ).pack(pady=(2, 20))

        # ── Form card ────────────────────────────────────────
        card = ctk.CTkFrame(
            self, fg_color=C["modal"], corner_radius=12,
            border_width=1, border_color=C["divider"]
        )
        card.pack(padx=36, pady=12, fill="x")

        def field(parent, icon, label, default="", show=""):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(14, 0))
            ctk.CTkLabel(
                row, text=f"{icon}  {label}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=C["txt_secondary"], anchor="w"
            ).pack(anchor="w")
            e = ctk.CTkEntry(
                parent, height=42, corner_radius=8,
                font=ctk.CTkFont(size=14),
                fg_color=C["input_bg"], border_color=C["divider"],
                text_color=C["txt_primary"],
                placeholder_text_color=C["txt_muted"],
                show=show
            )
            e.pack(fill="x", padx=20, pady=(4, 0))
            if default:
                e.insert(0, default)
            return e

        self.e_user = field(card, "👤", "Username", "")
        self.e_host = field(card, "🌐", "Server IP", CLIENT_DEFAULT_HOST)

        # Port row
        row_p = ctk.CTkFrame(card, fg_color="transparent")
        row_p.pack(fill="x", padx=20, pady=(14, 0))
        ctk.CTkLabel(
            row_p, text="🔌  Port",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["txt_secondary"], anchor="w"
        ).pack(anchor="w")
        self.e_port = ctk.CTkEntry(
            card, height=42, corner_radius=8,
            font=ctk.CTkFont(size=14),
            fg_color=C["input_bg"], border_color=C["divider"],
            text_color=C["txt_primary"],
            placeholder_text_color=C["txt_muted"]
        )
        self.e_port.insert(0, str(DEFAULT_PORT))
        self.e_port.pack(fill="x", padx=20, pady=(4, 0))

        # ── Error label ──────────────────────────────────────
        self.lbl_err = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont(size=11),
            text_color=C["red"]
        )
        self.lbl_err.pack(pady=(8, 0))

        # ── Connect button ───────────────────────────────────
        self.btn = ctk.CTkButton(
            card, text="Connect  →",
            height=46, corner_radius=10,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=C["green"], hover_color=C["green_dark"],
            text_color="white", command=self._do_connect
        )
        self.btn.pack(fill="x", padx=20, pady=(14, 22))

        # ── Footer ───────────────────────────────────────────
        ctk.CTkLabel(
            self, text="LAN + Remote • Python Chat",
            font=ctk.CTkFont(size=11), text_color=C["txt_muted"]
        ).pack(pady=8)

    def _do_connect(self):
        """Handle Connect button press."""
        username = self.e_user.get().strip()
        host     = self.e_host.get().strip()
        port_s   = self.e_port.get().strip()

        if not username:
            return self._err("Please enter a username.")
        if len(username) > 24:
            return self._err("Username max 24 characters.")
        if not host:
            return self._err("Please enter server IP.")
        try:
            port = int(port_s)
            assert 1 <= port <= 65535
        except Exception:
            return self._err("Enter a valid port (1–65535).")

        self._err("")
        self.btn.configure(text="Connecting...", state="disabled")
        self.update()
        self.on_connect(username, host, port)

    def _err(self, msg: str):
        self.lbl_err.configure(text=msg)
        if msg:
            self.btn.configure(text="Connect  →", state="normal")

    def show_error(self, msg: str):
        """External error (e.g. connection failed)."""
        self._err(msg)

    def close(self):
        try: self.destroy()
        except Exception: pass