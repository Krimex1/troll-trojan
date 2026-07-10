import socket, threading, time

HOST = '0.0.0.0'
PORT = 25154
urls = {}
TTL = 30
lock = threading.Lock()

def cleanup():
    now = time.time()
    expired = [k for k, v in list(urls.items()) if now - v > TTL]
    for k in expired:
        del urls[k]

def handle(c):
    global urls
    data = c.recv(4096)
    if not data: c.close(); return
    msg = data.decode().strip()
    with lock:
        cleanup()
        if msg.startswith('PUT '):
            url = msg[4:]
            if url and url != 'NONE':
                urls[url] = time.time()
            c.sendall(b'OK\n')
        elif msg == 'LIST':
            if urls:
                c.sendall(('\n'.join(urls.keys()) + '\n').encode())
            else:
                c.sendall(b'NONE\n')
        elif msg == 'GET':
            if urls:
                url = next(iter(urls))
                del urls[url]
                c.sendall(url.encode() + b'\n')
            else:
                c.sendall(b'NONE\n')
    c.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen(5)
print(f"Relay on {HOST}:{PORT} (TTL={TTL}s)")
while True:
    c, addr = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
