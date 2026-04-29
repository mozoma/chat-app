# ============================================================
# Full WhatsApp-like Main Chat Window

###Sujood Elsayed####
# ============================================================

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
from datetime import datetime

from config import (
    APP_NAME, MAIN_WIDTH, MAIN_HEIGHT, C,
    T_CHAT, T_PRIVATE, T_FILE, T_IMAGE, T_VOICE,
    T_USER_LIST, T_ROOM_LIST, T_HISTORY, T_SYSTEM, T_ERROR, T_PONG,
    DEFAULT_ROOM
)
from client import ChatClient
from users_panel import SidePanel
from media_handler import MediaHandler
from file_transfer import is_image, human_size, file_icon
from voice_msg import format_duration, PYAUDIO_OK

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ══════════════════════════════════════════════════════════════
# Private Chat Popup
# ══════════════════════════════════════════════════════════════

class PrivateChatWindow(ctk.CTkToplevel):
    """Private DM window between two users."""

    def __init__(self, parent, my_username: str, other: str,
                 on_send, media: MediaHandler):
        super().__init__(parent)
        self.my = my_username
        self.other = other
        self.on_send = on_send
        self.media   = media

        self.title(f"💬  {other}")
        self.geometry("440x600")
        self.configure(fg_color=C["bg"])
        self._build()
        self.bind("<Return>", lambda e: self._send())
        self.lift(); self.focus_force()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["header"],
                           corner_radius=0, height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text=self.other[:2].upper(),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white", fg_color=C["green"],
            width=38, height=38, corner_radius=19
        ).pack(side="left", padx=12, pady=9)

        info = ctk.CTkFrame(hdr, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text=self.other,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["txt_primary"]).pack(anchor="w")
        ctk.CTkLabel(info, text="online",
                     font=ctk.CTkFont(size=11),
                     text_color=C["online"]).pack(anchor="w")

        # Messages
        self.msg_frame = ctk.CTkScrollableFrame(
            self, fg_color=C["bg"],
            scrollbar_button_color=C["divider"]
        )
        self.msg_frame.pack(fill="both", expand=True)

        # Input bar
        bar = ctk.CTkFrame(self, fg_color=C["header"],
                           corner_radius=0, height=60)
        bar.pack(fill="x"); bar.pack_propagate(False)

        # Attach button
        ctk.CTkButton(
            bar, text="📎", width=36, height=36,
            corner_radius=18, fg_color="transparent",
            hover_color=C["hover"], font=ctk.CTkFont(size=18),
            text_color=C["txt_secondary"], command=self._attach
        ).pack(side="left", padx=(8, 0), pady=12)

        self.entry = ctk.CTkEntry(
            bar, placeholder_text="Type a message",
            height=38, corner_radius=20,
            font=ctk.CTkFont(size=13),
            fg_color=C["input_bg"], border_color=C["divider"],
            text_color=C["txt_primary"],
            placeholder_text_color=C["txt_muted"]
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=8)
        self.entry.focus_set()

        ctk.CTkButton(
            bar, text="➤", width=38, height=38,
            corner_radius=19, fg_color=C["green"],
            hover_color=C["green_dark"],
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white", command=self._send
        ).pack(side="right", padx=(0, 10))

    def _send(self):
        msg = self.entry.get().strip()
        if not msg: return
        self.entry.delete(0, "end")
        self.add_bubble(self.my, msg, is_me=True)
        self.on_send(self.other, msg)

    def _attach(self):
        path = self.media.pick_file()
        if not path: return
        info = self.media.prepare_file(path)
        if not info: return
        self.add_file_bubble(self.my, info, is_me=True)
        self.on_send(
            self.other, f"[FILE:{info['filename']}]",
            msg_type="FILE", filename=info["filename"],
            filesize=info["filesize"], b64data=info["data"]
        )

    # ── Message display ──────────────────────────────────────

    def add_bubble(self, sender: str, text: str,
                   timestamp: str = "", is_me: bool = None):
        if is_me is None:
            is_me = sender == self.my
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")
        _add_text_bubble(self.msg_frame, sender, text,
                         timestamp, is_me, is_dm=True)
        self._scroll()

    def add_file_bubble(self, sender: str, info: dict,
                        is_me: bool = True, b64data: str = None):
        _add_file_bubble(self.msg_frame, sender, info,
                         is_me, b64data, self.media)
        self._scroll()

    def add_image_bubble(self, sender: str, filename: str,
                         b64data: str, is_me: bool = False,
                         timestamp: str = ""):
        _add_image_bubble(self.msg_frame, sender, filename,
                          b64data, is_me, timestamp, self.media)
        self._scroll()

    def add_voice_bubble(self, sender: str, duration: float,
                         b64data: str, is_me: bool = False,
                         timestamp: str = ""):
        _add_voice_bubble(self.msg_frame, sender, duration,
                          b64data, is_me, timestamp, self.media)
        self._scroll()

    def add_history(self, messages: list):
        for m in messages:
            mt = m.get("msg_type", "CHAT")
            s  = m.get("sender", "")
            ts = m.get("timestamp", "")[-5:]
            c  = m.get("content", "")
            me = s == self.my
            if mt == "CHAT":
                self.add_bubble(s, c, ts, me)

    def _scroll(self):
        try:
            self.after(60, lambda:
                self.msg_frame._parent_canvas.yview_moveto(1.0))
        except Exception: pass

    def bring_front(self):
        self.lift(); self.focus_force()


# ══════════════════════════════════════════════════════════════
#  Shared bubble rendering helpers
# ══════════════════════════════════════════════════════════════

def _add_text_bubble(parent, sender: str, text: str,
                     timestamp: str, is_me: bool,
                     is_dm: bool = False):
    """Plain text message bubble."""
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="x", padx=10, pady=2)

    bg  = C["bubble_out"] if is_me else C["bubble_in"]
    side = "right" if is_me else "left"

    wrap = ctk.CTkFrame(outer, fg_color=bg, corner_radius=10)
    wrap.pack(side=side, anchor="e" if is_me else "w")

    if not is_me and not is_dm:
        ctk.CTkLabel(
            wrap, text=sender,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C["green_light"], anchor="w"
        ).pack(padx=10, pady=(6, 0), anchor="w")

    ctk.CTkLabel(
        wrap, text=text,
        font=ctk.CTkFont(size=13),
        text_color=C["txt_primary"],
        wraplength=320, justify="left", anchor="w"
    ).pack(padx=10, pady=(4, 2), anchor="w")

    ctk.CTkLabel(
        wrap, text=f"{timestamp}  ✓✓" if is_me else timestamp,
        font=ctk.CTkFont(size=10),
        text_color=C["txt_muted"],
        anchor="e" if is_me else "w"
    ).pack(padx=10, pady=(0, 5), anchor="e" if is_me else "w")


def _add_system_bubble(parent, text: str):
    """Centered system message."""
    ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(size=11, slant="italic"),
        text_color=C["txt_muted"],
        fg_color=C["header"],
        corner_radius=8,
        padx=10, pady=3
    ).pack(pady=4)

#########################################################################################################################
            #Seif Mohamed#
########################################################################################################################
def _add_file_bubble(parent, sender: str, info: dict,
                     is_me: bool, b64data: str,
                     media: MediaHandler):
    """File attachment bubble."""
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="x", padx=10, pady=2)

    bg   = C["bubble_out"] if is_me else C["bubble_in"]
    side = "right" if is_me else "left"

    wrap = ctk.CTkFrame(outer, fg_color=bg, corner_radius=10)
    wrap.pack(side=side)

    row = ctk.CTkFrame(wrap, fg_color="transparent")
    row.pack(padx=10, pady=8, fill="x")

    icon = info.get("icon", "📎")
    ctk.CTkLabel(
        row, text=icon,
        font=ctk.CTkFont(size=28)
    ).pack(side="left", padx=(0, 8))

    info_col = ctk.CTkFrame(row, fg_color="transparent")
    info_col.pack(side="left")

    ctk.CTkLabel(
        info_col, text=info.get("filename", "file"),
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=C["txt_primary"], anchor="w",
        wraplength=200
    ).pack(anchor="w")
    ctk.CTkLabel(
        info_col, text=info.get("human_size", ""),
        font=ctk.CTkFont(size=11),
        text_color=C["txt_secondary"]
    ).pack(anchor="w")

    if not is_me and b64data:
        ctk.CTkButton(
            wrap, text="⬇  Download",
            height=30, corner_radius=6,
            font=ctk.CTkFont(size=12),
            fg_color=C["green"], hover_color=C["green_dark"],
            command=lambda: media.download_file(
                b64data, info.get("filename", "file"))
        ).pack(padx=10, pady=(0, 8), anchor="w")


def _add_image_bubble(parent, sender: str, filename: str,
                      b64data: str, is_me: bool, timestamp: str,
                      media: MediaHandler):
    """Image bubble with thumbnail preview."""
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="x", padx=10, pady=2)

    bg   = C["bubble_out"] if is_me else C["bubble_in"]
    side = "right" if is_me else "left"

    wrap = ctk.CTkFrame(outer, fg_color=bg, corner_radius=10)
    wrap.pack(side=side)

    if not is_me:
        ctk.CTkLabel(
            wrap, text=sender,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C["green_light"], anchor="w"
        ).pack(padx=10, pady=(6, 0), anchor="w")

    # Thumbnail
    thumb = media.b64_thumbnail(b64data) if b64data else None
    if thumb:
        lbl_img = tk.Label(wrap, image=thumb,
                           bg=bg, cursor="hand2")
        lbl_img.image = thumb
        lbl_img.pack(padx=8, pady=6)
        lbl_img.bind(
            "<Button-1>",
            lambda e: media.show_fullsize_image(b64data=b64data)
        )
    else:
        ctk.CTkLabel(
            wrap, text=f"🖼  {filename}",
            font=ctk.CTkFont(size=12),
            text_color=C["txt_primary"]
        ).pack(padx=10, pady=6)
        ctk.CTkButton(
            wrap, text="View",
            height=26, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=C["green"],
            command=lambda: media.show_fullsize_image(b64data=b64data)
        ).pack(padx=8, pady=(0, 6))

    ctk.CTkLabel(
        wrap, text=timestamp,
        font=ctk.CTkFont(size=10),
        text_color=C["txt_muted"]
    ).pack(padx=10, pady=(0, 5), anchor="e" if is_me else "w")


def _add_voice_bubble(parent, sender: str, duration: float,
                      b64data: str, is_me: bool, timestamp: str,
                      media: MediaHandler):
    """Voice message bubble."""
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="x", padx=10, pady=2)

    bg   = C["bubble_out"] if is_me else C["bubble_in"]
    side = "right" if is_me else "left"

    wrap = ctk.CTkFrame(outer, fg_color=bg, corner_radius=10)
    wrap.pack(side=side)

    if not is_me:
        ctk.CTkLabel(
            wrap, text=sender,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C["green_light"]
        ).pack(padx=10, pady=(6, 0), anchor="w")

    row = ctk.CTkFrame(wrap, fg_color="transparent")
    row.pack(padx=10, pady=(6, 4))

    # Waveform visualization (decorative bars)
    wave_canvas = tk.Canvas(row, width=120, height=28,
                            bg=bg, highlightthickness=0)
    wave_canvas.pack(side="left", padx=(0, 8))
    _draw_waveform(wave_canvas, bg)

    dur_str = format_duration(duration)
    lbl_dur = ctk.CTkLabel(
        row, text=dur_str,
        font=ctk.CTkFont(size=11),
        text_color=C["txt_secondary"]
    )
    lbl_dur.pack(side="left", padx=(0, 6))

    # Play/Pause toggle
    playing = {"state": False}
    btn_play = ctk.CTkButton(
        row, text="▶",
        width=34, height=34, corner_radius=17,
        font=ctk.CTkFont(size=14),
        fg_color=C["green"], hover_color=C["green_dark"],
        text_color="white"
    )
    btn_play.pack(side="left")

    def on_done():
        playing["state"] = False
        try: btn_play.configure(text="▶")
        except Exception: pass

    def toggle():
        if not playing["state"]:
            playing["state"] = True
            btn_play.configure(text="⏸")
            media.play_voice_b64(b64data, on_done=on_done)
        else:
            playing["state"] = False
            btn_play.configure(text="▶")
            media.stop_playback()

    btn_play.configure(command=toggle)

    ctk.CTkLabel(
        wrap, text=timestamp,
        font=ctk.CTkFont(size=10),
        text_color=C["txt_muted"]
    ).pack(padx=10, pady=(0, 5), anchor="e" if is_me else "w")


def _draw_waveform(canvas: tk.Canvas, bg_color: str):
    """Draw decorative waveform bars."""
    import random
    random.seed(42)
    canvas.delete("all")
    bar_w = 3
    gap   = 2
    x     = 2
    while x < 118:
        h = random.randint(4, 24)
        y1 = (28 - h) // 2
        y2 = y1 + h
        canvas.create_rectangle(x, y1, x + bar_w, y2,
                                 fill=C["green"], outline="")
        x += bar_w + gap


# ══════════════════════════════════════════════════════════════
#  Main Chat Window
# ══════════════════════════════════════════════════════════════

class MainChatWindow(ctk.CTk):
    """
    Full WhatsApp-like main chat window.
    """

    def __init__(self):
        super().__init__()
        self.chat_client: ChatClient = None
        self.username    = ""
        self.cur_room    = DEFAULT_ROOM
        self.media       = MediaHandler()

        # Open DM windows
        self._dm: dict[str, PrivateChatWindow] = {}

        self.title(APP_NAME)
        self.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}")
        self.minsize(900, 580)
        self.configure(fg_color=C["bg"])
        self._center()
        self._build()
        self.withdraw()
        self.after(100, self._show_login)
        self.protocol("WM_DELETE_WINDOW", self._close)

        # Voice recording state
        self._recording = False

    # ─── Window setup ────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - MAIN_WIDTH)  // 2
        y = (self.winfo_screenheight() - MAIN_HEIGHT) // 2
        self.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}+{x}+{y}")

    def _build(self):
        """Build main structure."""
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)

        # ── Left panel ───────────────────────────────────────
        self.side = SidePanel(
            main,
            my_username="",
            on_user_click=self._open_dm,
            on_room_click=self._switch_room,
            on_create_room=self._create_room_dialog
        )
        self.side.pack(side="left", fill="y")

        ctk.CTkFrame(main, width=1, fg_color=C["divider"],
                     corner_radius=0).pack(side="left", fill="y")

        # ── Right: chat area ─────────────────────────────────
        right = ctk.CTkFrame(main, fg_color=C["bg"], corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        self._build_chat_header(right)
        self._build_messages_area(right)
        self._build_input_bar(right)

    def _build_chat_header(self, parent):
        """Chat title bar."""
        self.chat_hdr = ctk.CTkFrame(
            parent, fg_color=C["header"],
            corner_radius=0, height=56
        )
        self.chat_hdr.pack(fill="x")
        self.chat_hdr.pack_propagate(False)

        self.lbl_room = ctk.CTkLabel(
            self.chat_hdr,
            text="# General",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C["txt_primary"]
        )
        self.lbl_room.pack(side="left", padx=16)

        self.lbl_members = ctk.CTkLabel(
            self.chat_hdr,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C["txt_secondary"]
        )
        self.lbl_members.pack(side="left", padx=4)

        # Status / username (right)
        self.lbl_status = ctk.CTkLabel(
            self.chat_hdr,
            text="⚪ Disconnected",
            font=ctk.CTkFont(size=11),
            text_color=C["txt_muted"]
        )
        self.lbl_status.pack(side="right", padx=16)

    def _build_messages_area(self, parent):
        """Messages area."""
        self.msg_area = ctk.CTkScrollableFrame(
            parent, fg_color=C["bg"],
            scrollbar_button_color=C["divider"],
            scrollbar_button_hover_color=C["green"]
        )
        self.msg_area.pack(fill="both", expand=True)

    def _build_input_bar(self, parent):
        """Bottom input bar."""
        bar = ctk.CTkFrame(
            parent, fg_color=C["header"],
            corner_radius=0, height=64
        )
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Attach (file/image)
        ctk.CTkButton(
            bar, text="📎",
            width=40, height=40, corner_radius=20,
            fg_color="transparent", hover_color=C["hover"],
            font=ctk.CTkFont(size=22),
            text_color=C["txt_secondary"],
            command=self._attach
        ).pack(side="left", padx=(10, 2), pady=12)

        # Image button
        ctk.CTkButton(
            bar, text="🖼",
            width=40, height=40, corner_radius=20,
            fg_color="transparent", hover_color=C["hover"],
            font=ctk.CTkFont(size=20),
            text_color=C["txt_secondary"],
            command=self._attach_image
        ).pack(side="left", padx=2, pady=12)

        # Voice button (hold to record)
        self.btn_voice = ctk.CTkButton(
            bar, text="🎤",
            width=40, height=40, corner_radius=20,
            fg_color="transparent", hover_color=C["hover"],
            font=ctk.CTkFont(size=20),
            text_color=C["txt_secondary"],
            command=None
        )
        self.btn_voice.pack(side="left", padx=2, pady=12)
        self.btn_voice.bind("<ButtonPress-1>",   self._voice_start)
        self.btn_voice.bind("<ButtonRelease-1>", self._voice_stop)

        # Message entry
        self.entry = ctk.CTkEntry(
            bar,
            placeholder_text="Type a message",
            height=40, corner_radius=20,
            font=ctk.CTkFont(size=14),
            fg_color=C["input_bg"],
            border_color=C["divider"],
            text_color=C["txt_primary"],
            placeholder_text_color=C["txt_muted"]
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())

        # Send
        ctk.CTkButton(
            bar, text="➤",
            width=42, height=42, corner_radius=21,
            fg_color=C["green"], hover_color=C["green_dark"],
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white", command=self._send
        ).pack(side="right", padx=(0, 12))

        # Recording indicator label
        self.lbl_rec = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["red"]
        )
        self.lbl_rec.place(x=0, y=0)  # hidden initially

    # ─── Login ───────────────────────────────────────────────

    def _show_login(self):
        from login_screen import LoginScreen
        self.login = LoginScreen(on_connect=self._attempt_connect)
        self.login.grab_set()

    def _attempt_connect(self, username: str, host: str, port: int):
        self.username = username
        self.chat_client = ChatClient(
            host, port, username,
            on_message=self._on_packet,
            on_connect=self._on_connected,
            on_disconnect=self._on_disconnected
        )
        self.side.my_username = username

        def _t():
            ok = self.chat_client.connect()
            if not ok:
                self.after(0, lambda: self.login.show_error(
                    "❌ Cannot connect. Check server IP/port."
                ))
        threading.Thread(target=_t, daemon=True).start()

    def _on_connected(self):
        self.after(0, self._on_connected_ui)

    def _on_connected_ui(self):
        try:
            self.login.close()
        except Exception:
            pass
        self.deiconify(); self.lift(); self.focus_force()
        self.lbl_status.configure(
            text=f"🟢  {self.username}", text_color=C["green_light"]
        )
        self._set_room(DEFAULT_ROOM)
        self.entry.focus_set()

    def _on_disconnected(self, reason: str):
        self.after(0, lambda: self.lbl_status.configure(
            text="🔴  Disconnected", text_color=C["red"]
        ))

    # ─── Packet handler ──────────────────────────────────────

    def _on_packet(self, pkt: dict):
        self.after(0, lambda p=pkt: self._dispatch(p))

    def _dispatch(self, pkt: dict):
        t = pkt.get("type", "")

        if t == T_CHAT:
            u, r, c, ts = (
                pkt.get("username", ""),
                pkt.get("room", ""),
                pkt.get("content", ""),
                pkt.get("timestamp", "")
            )
            if r == self.cur_room:
                _add_text_bubble(self.msg_area, u, c, ts, u == self.username)
                self._scroll()

        elif t == T_PRIVATE:
            self._handle_private(pkt)

        elif t == T_FILE:
            self._handle_media_pkt(pkt, is_img=False)

        elif t == T_IMAGE:
            self._handle_media_pkt(pkt, is_img=True)

        elif t == T_VOICE:
            self._handle_voice_pkt(pkt)

        elif t == T_USER_LIST:
            self.side.update_users(pkt.get("users", []))

        elif t == T_ROOM_LIST:
            rooms = pkt.get("rooms", [])
            self.side.update_rooms(rooms)

        elif t == T_HISTORY:
            if pkt.get("room") == self.cur_room:
                self._load_history(pkt.get("messages", []))

        elif t == T_SYSTEM:
            _add_system_bubble(self.msg_area, pkt.get("content", ""))
            self._scroll()

        elif t == T_ERROR:
            _add_system_bubble(self.msg_area,
                               f"⚠️  {pkt.get('content', '')}")
            self._scroll()

    def _handle_private(self, pkt: dict):
        sender   = pkt.get("sender", "")
        receiver = pkt.get("receiver", "")
        content  = pkt.get("content", "")
        mt       = pkt.get("msg_type", "CHAT")
        ts       = pkt.get("timestamp", "")
        other    = receiver if sender == self.username else sender

        win = self._get_dm(other)

        if mt == "CHAT":
            is_me = sender == self.username
            win.add_bubble(sender, content, ts, is_me)

        elif mt in ("FILE", "IMAGE"):
            fname  = pkt.get("filename", "file")
            fsize  = pkt.get("filesize", 0)
            b64    = pkt.get("data", "")
            is_me  = sender == self.username
            if mt == "IMAGE":
                win.add_image_bubble(sender, fname, b64, is_me, ts)
            else:
                info = {
                    "filename": fname,
                    "filesize": fsize,
                    "human_size": human_size(fsize or 0),
                    "icon": file_icon(fname)
                }
                win.add_file_bubble(sender, info, is_me, b64data=b64)

        elif mt == "VOICE":
            dur  = pkt.get("duration", 0)
            b64  = pkt.get("data", "")
            is_me = sender == self.username
            win.add_voice_bubble(sender, dur, b64, is_me, ts)

    def _handle_media_pkt(self, pkt: dict, is_img: bool):
        sender  = pkt.get("sender", "")
        target  = pkt.get("target", "")
        fname   = pkt.get("filename", "file")
        fsize   = pkt.get("filesize", 0)
        b64     = pkt.get("data", "")
        ts      = pkt.get("timestamp", "")
        is_me   = sender == self.username

        if target == self.cur_room:
            if is_img:
                _add_image_bubble(self.msg_area, sender, fname,
                                  b64, is_me, ts, self.media)
            else:
                info = {
                    "filename": fname,
                    "filesize": fsize,
                    "human_size": human_size(fsize or 0),
                    "icon": file_icon(fname)
                }
                _add_file_bubble(self.msg_area, sender, info,
                                 is_me, b64, self.media)
            self._scroll()

    def _handle_voice_pkt(self, pkt: dict):
        sender = pkt.get("sender", "")
        target = pkt.get("target", "")
        dur    = pkt.get("duration", 0.0)
        b64    = pkt.get("data", "")
        ts     = pkt.get("timestamp", "")
        is_me  = sender == self.username

        if target == self.cur_room:
            _add_voice_bubble(self.msg_area, sender, dur,
                              b64, is_me, ts, self.media)
            self._scroll()

    # ─── History ─────────────────────────────────────────────

    def _load_history(self, messages: list):
        for w in self.msg_area.winfo_children():
            w.destroy()

        if messages:
            _add_system_bubble(self.msg_area, "── Chat History ──")
            for m in messages:
                mt = m.get("msg_type", "CHAT")
                u  = m.get("username", "")
                c  = m.get("content", "")
                ts = m.get("timestamp", "")[-5:]
                me = u == self.username
                if mt == "CHAT":
                    _add_text_bubble(self.msg_area, u, c, ts, me)
            _add_system_bubble(self.msg_area, "── Live Chat ──")
        else:
            _add_system_bubble(
                self.msg_area, f"Welcome to #{self.cur_room}! 👋"
            )
        self._scroll()

    # ─── Send ────────────────────────────────────────────────

    def _send(self):
        msg = self.entry.get().strip()
        if not msg: return
        if not self._check_connected(): return
        self.entry.delete(0, "end")
        self.chat_client.send_message(msg, self.cur_room)

    def _attach(self): 
        if not self._check_connected(): return
        path = self.media.pick_file()
        if not path: return
        info = self.media.prepare_file(path)
        if not info: return

        img_flag = info["is_image"]
        self.chat_client.send_file(
            self.cur_room, info["filename"],
            info["filesize"], info["data"],
            is_image=img_flag, is_private=False
        )
        if img_flag:
            _add_image_bubble(self.msg_area, self.username,
                              info["filename"], info["data"],
                              True, datetime.now().strftime("%H:%M"),
                              self.media)
        else:
            _add_file_bubble(self.msg_area, self.username,
                             info, True, info["data"], self.media)
        self._scroll()

    def _attach_image(self):
        if not self._check_connected(): return
        path = self.media.pick_image()
        if not path: return
        info = self.media.prepare_file(path)
        if not info: return
        self.chat_client.send_file(
            self.cur_room, info["filename"],
            info["filesize"], info["data"],
            is_image=True, is_private=False
        )
        _add_image_bubble(self.msg_area, self.username,
                          info["filename"], info["data"],
                          True, datetime.now().strftime("%H:%M"),
                          self.media)
        self._scroll()

    # ─── Voice recording ─────────────────────────────────────

    def _voice_start(self, event=None):
        if not self._check_connected(): return
        if not PYAUDIO_OK:
            messagebox.showinfo("Voice", "Install pyaudio to record voice messages.")
            return
        if self.media.start_recording():
            self._recording = True
            self.btn_voice.configure(
                fg_color=C["red"], text_color="white"
            )
            self.lbl_rec.configure(text="● Recording...")
            self.lbl_rec.place(x=56, y=22)
            self._update_rec_timer()

    def _voice_stop(self, event=None):
        if not self._recording: return
        self._recording = False
        self.btn_voice.configure(
            fg_color="transparent", text_color=C["txt_secondary"]
        )
        self.lbl_rec.place_forget()

        filepath, duration = self.media.stop_recording()
        if not filepath or duration < 0.5:
            return  # too short

        info = self.media.prepare_voice(filepath, duration)
        if not info: return

        self.chat_client.send_voice(
            self.cur_room, duration, info["data"], is_private=False
        )
        _add_voice_bubble(self.msg_area, self.username,
                          duration, info["data"],
                          True, datetime.now().strftime("%H:%M"),
                          self.media)
        self._scroll()

    def _update_rec_timer(self):
        if not self._recording: return
        dur = self.media.recording_duration()
        self.lbl_rec.configure(
            text=f"● {format_duration(dur)}  Recording..."
        )
        self.after(200, self._update_rec_timer)

    # ─── Rooms ───────────────────────────────────────────────

    def _switch_room(self, room: str):
        if room == self.cur_room: return
        self._set_room(room)
        if self.chat_client and self.chat_client.connected:
            self.chat_client.join_room(room)

    def _set_room(self, room: str):
        self.cur_room = room
        if self.chat_client:
            self.chat_client.current_room = room
        self.lbl_room.configure(text=f"# {room}")
        self.side.set_active_room(room)

    def _create_room_dialog(self):
        dlg = ctk.CTkInputDialog(
            text="Enter new room name:", title="Create Room"
        )
        name = dlg.get_input()
        if name and name.strip():
            name = name.strip()
            if self.chat_client and self.chat_client.connected:
                self.chat_client.create_room(name)

    # ─── DM management ───────────────────────────────────────

    def _get_dm(self, other: str) -> PrivateChatWindow:
        """Ensure DM window exists, return it."""
        if other in self._dm:
            w = self._dm[other]
            if w.winfo_exists():
                return w
            del self._dm[other]

        def _send_pm(recv, content, msg_type="CHAT",
                     filename=None, filesize=None, b64data=None):
            if self.chat_client and self.chat_client.connected:
                self.chat_client.send_private(
                    recv, content,
                    msg_type=msg_type,
                    filename=filename, filesize=filesize,
                    b64data=b64data
                )

        win = PrivateChatWindow(
            self, self.username, other, _send_pm, self.media
        )
        self._dm[other] = win

        # Load history from DB
        try:
            from database import Database
            db = Database()
            hist = db.get_private_history(self.username, other)
            if hist:
                win.add_history(hist)
        except Exception:
            pass

        def _close():
            if other in self._dm:
                del self._dm[other]
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _close)
        return win

    def _open_dm(self, other: str):
        win = self._get_dm(other)
        win.bring_front()

    # ─── Helpers ─────────────────────────────────────────────

    def _scroll(self):
        try:
            self.after(60, lambda:
                self.msg_area._parent_canvas.yview_moveto(1.0))
        except Exception: pass

    def _check_connected(self) -> bool:
        if not self.chat_client or not self.chat_client.connected:
            messagebox.showwarning("Not Connected",
                                   "You are not connected to a server.")
            return False
        return True

    def _close(self):
        if self.chat_client:
            self.chat_client.disconnect()
        self.destroy()

    def run(self):
        self.mainloop()


# ─── Entry point ─────────────────────────────────────────────

if __name__ == "__main__":
    MainChatWindow().run()