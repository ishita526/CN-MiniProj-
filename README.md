# Python-Based Client-Server Chat Application

A complete Computer Networks mini-project demonstrating **Transport Layer (TCP)** communication, **multithreaded socket programming**, **real-time message broadcasting**, **persistent audit logging**, and a **modern web client** connected via a protocol bridge gateway.

---

## 📌 Architecture Overview

```text
[ Browser 1 (Vaishnavi) ]       [ Browser 2 (Ishita) ]       [ Terminal Client (Shree) ]
            │                               │                                     │
            │ WebSocket (ws://)             │ WebSocket (ws://)                   │
            ▼                               ▼                                     │
┌────────────────────────────────────────────────────────┐                        │
│                WebSocket Bridge Gateway                │                        │
│                 (websocket_bridge.py)                  │                        │
│         Translates WebSockets <---> TCP Socket         │                        │
└────────────────────────────────────────────────────────┘                        │
            │                               │                                     │
            │ TCP Socket                    │ TCP Socket                          │ TCP Socket
            └───────────────────────┬───────┴─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Core TCP Socket Server                                │
│                                (server.py)                                      │
│                               127.0.0.1:5000                                    │
│                                                                                 │
│   • Multi-Client Threading        • Central Message Broadcast                   │
│   • Dynamic Online User Registry  • Persistent Logging (chat_logs.txt)          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Computer Networks Concepts

1. **Client-Server Architecture**:
   - Centralized server acts as the authoritative hub. Clients connect to the server and never need to discover or communicate directly with each other.
2. **TCP (Transmission Control Protocol)**:
   - **Connection-oriented**: Requires a 3-way handshake (`SYN` $\rightarrow$ `SYN-ACK` $\rightarrow$ `ACK`) before data flows.
   - **Reliable & Ordered**: Ensures every message packet arrives intact, in order, with automatic retransmission if dropped.
3. **Sockets & Addressing**:
   - A socket is an endpoint represented by an `(IP, Port)` tuple (`127.0.0.1:5000`).
   - The OS uses ephemeral source ports to demultiplex different clients simultaneously connected to the same destination port `5000`.
4. **Multithreading & Concurrency**:
   - `recv()` is a blocking operation. The server spawns a dedicated worker thread (`threading.Thread`) for each connected client to read incoming bytes independently.
5. **Thread Synchronization (Mutex / Locks)**:
   - `threading.Lock` protects shared resources (the connected clients dictionary and file writes to `chat_logs.txt`), preventing race conditions.
6. **Protocol Gateway / Bridging**:
   - Standard browser sandboxes prevent JavaScript from creating raw TCP sockets. The WebSocket bridge acts as a transport-level translation gateway (`WebSocket frames` $\leftrightarrow$ `raw TCP byte stream`).

---

## 📁 Project Structure

```text
CN MiniProj/
│
├── server.py              # Core Python TCP socket server (127.0.0.1:5000)
├── client.py              # Terminal-based TCP client with background listener
├── websocket_bridge.py    # Gateway bridging Browser WebSockets to the TCP server
├── chat_logs.txt          # Persistent audit log of all chat activity
├── README.md              # Project documentation
├── .gitignore             # Git ignore configuration
│
└── frontend/
    ├── index.html         # User interface layout (Join card, Chat room, Sidebar)
    ├── style.css          # Restrained, desktop-first stylesheet
    └── script.js          # Client-side logic & WebSocket event handling
```

---

## 🛠️ Prerequisites & Installation

- **Python 3.10+**
- Required library: `websockets`

Install dependencies using pip:
```bash
pip install websockets
```

---

## 💻 How to Run the Application

### Option A: Web Browser Interface (Recommended)

Run the following in **three separate terminal windows**:

#### 1. Start the TCP Server:
```powershell
python server.py
```
*Output:*
```text
[*] Server bound to 127.0.0.1:5000
[*] Server is listening. Logs are saved to 'chat_logs.txt'.
[*] Waiting for clients...
```

#### 2. Start the WebSocket Bridge:
```powershell
python websocket_bridge.py
```
*Output:*
```text
[*] Starting WebSocket Bridge on ws://127.0.0.1:8765
[*] Relaying to TCP Chat Server on 127.0.0.1:5000
[*] WebSocket Bridge is running. Waiting for browser clients...
```

#### 3. Open the Frontend:
Open `frontend/index.html` in your browser, or start a local server:
```powershell
python -m http.server 8000 --directory frontend
```
Navigate to:
```text
http://127.0.0.1:8000
```
Open multiple tabs (e.g. one for "Vaishnavi", one for "Ishita"), enter usernames, and chat in real-time!

---

### Option B: Terminal-Only Mode

You can also chat entirely from command-line terminals without any browser:

1. **Terminal 1 (Server):**
   ```powershell
   python server.py
   ```
2. **Terminal 2 (Client 1):**
   ```powershell
   python client.py
   # Enter username: Alice
   ```
3. **Terminal 3 (Client 2):**
   ```powershell
   python client.py
   # Enter username: Bob
   ```

---

## 📝 Persistent Chat Logs (`chat_logs.txt`)

Every session event and message is safely recorded with accurate local timestamps:
```text
[2026-10-08 22:15:33] SYSTEM: ishita joined the chat
[2026-10-08 22:15:34] SYSTEM: shree joined the chat
[2026-10-08 22:15:36] SYSTEM: vaishnavi joined the chat
[2026-10-08 22:15:41] ishita: hiiii
[2026-10-08 22:15:46] shree: hiiiiieeeeeeee
[2026-10-08 22:15:54] SYSTEM: ishita left the chat
[2026-10-08 22:16:00] SYSTEM: vaishnavi left the chat
```

---

## 🔒 Graceful Disconnection

- Type `exit` in the terminal or web chat to disconnect cleanly.
- The server detects the disconnect event, cleans up socket descriptors, updates online counts, notifies remaining peers, and logs the exit event.
