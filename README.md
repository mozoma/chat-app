# 💬 WhatsApp-like Chat App — Python

# A complete LAN + Remote chat application with file sharing, image sharing, and voice messages.
1	 Mohamed Hazem	media_handler.py+ server.py+ media_handler.py+	database.py
2	Seif Mohamed	client.py+ file_transfer.py+ private_msg.py
3	Hazem Essam	config.py+ users_panel.py+rooms.py 
4	Sujood Elsayed                      gui.py



## File Structure
```
whatsapp_chat/
├── config.py          → All settings, colors, message types
├── database.py        → SQLite: messages, files, users, rooms
├── server.py          → Multi-threaded server
├── client.py          → Client connection + auto-reconnect
├── rooms.py           → Thread-safe room manager
├── private_msg.py     → PM routing + all packet builders
├── file_transfer.py   → File encode/decode/thumbnail helpers
├── voice_msg.py       → PyAudio recording + WAV playback
├── media_handler.py   → Unified media API for GUI
├── login_screen.py    → WhatsApp-style login screen
├── users_panel.py     → Left panel (users + rooms)
├── gui.py             → Main chat window (entry point)
│
├── media/             → Received files/images
├── uploads/           → Server-side file storage
├── voice/             → Voice message WAV files
└── requirements.txt
```

---

## Installation
```bash
pip install customtkinter Pillow pyaudio
```
> **Windows pyaudio**: `pip install pipwin && X`  
> **macOS**: `brew install portaudio && pip install pyaudio`  
> **Linux**: `sudo apt install python3-pyaudio`

---

## Running

### 1. Start Server
```bash
python server.py
# Custom port:
python server.py 6000
```

### 2. Start Client
```bash
python gui.py
```
Enter your username, server IP, and port in the login screen.

---

## Features

### 💬 Chat
- Real-time messaging in rooms/groups
- WhatsApp-style message bubbles (green = sent, gray = received)
- Chat history loaded on room join (last 60 messages)
- Timestamps on every message

### 📎 File Transfer
- Send any file type (PDF, ZIP, DOCX, etc.)
- Shows file icon + name + size
- Download button for received files
- Max file size: 100 MB (configurable in `config.py`)

### 🖼 Image Sharing
- Send images with thumbnail preview in chat
- Click thumbnail to view full size
- Supports: JPG, PNG, GIF, WEBP, BMP

### 🎤 Voice Messages
- Hold the 🎤 button to record
- Release to send
- Play/pause button with waveform visualization
- Shows recording duration

### 👥 Rooms / Groups
- Default rooms: General, Tech Talk, Random
- Create new rooms with `+ New Room`
- Click any room to join and see its history

### 💬 Private Messages
- Click any user's 💬 button to open a DM window
- Send text, files, images, and voice in DMs
- History loaded from database

### 🔄 Auto-Reconnect
- Automatically retries 5 times on disconnect
- Configurable delay between attempts (`RECONNECT_DELAY`)

---

## Remote Access (Outside LAN)

1. Server already listens on `0.0.0.0` (all interfaces)
2. Forward port `5555` (TCP) on your router to server machine
3. Clients connect using your **public IP address**

### Optional: ngrok tunnel
```bash
ngrok tcp 5555
# Use the ngrok hostname and port in the client login screen
```

---

## Protocol
All messages use **newline-delimited JSON**:
```json
{
  "type": "CHAT|FILE|IMAGE|VOICE|PRIVATE|SYSTEM|...",
  "sender": "username",
  "target": "room_name or username",
  "content": "text",
  "filename": "optional",
  "filesize": 12345,
  "data": "base64_encoded_bytes",
  "timestamp": "HH:MM"
}
```
