"""
Neura-AI v1000 - "Hardcode" all-in-one main.py
Features included (high level):
- Flask web app with premium neon UI served inline
- Bot engine (chat, memory, persona, conversation history)
- Endpoints: /, /ask, /command, /health, /admin, /metrics, /upload
- Admin basic auth using env var ADMIN_TOKEN
- Rate limiting, request logging, usage metering
- File-based memory (safe for small scale)
- Tooling endpoints: summarize, translate, code_helper, imagesuggest
- Background scheduler & worker queue (threaded)
- Feature flags and safe mode
- Optional Gradio integration (if installed)
- Safe OpenAI client usage via environment variable OPENAI_API_KEY
- Configurable model (env NEURA_MODEL)
- Minimal templating served from strings (no external files required)
- Static-ish assets embedded via CSS in the HTML template
- Notes: keep your API key secret; rotate keys if leaked
"""

import os
import sys
import time
import json
import uuid
import math
import queue
import atexit
import base64
import logging
import threading
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, List, Optional, Tuple

from flask import (
    Flask, request, jsonify, abort, Response,
    render_template_string, send_file
)
from flask_cors import CORS

# Optional imports; fine to be missing in minimal env
try:
    import openai
except Exception:
    openai = None

try:
    import gradio as gr
except Exception:
    gr = None

# -------------------------------
# Configuration / Environment
# -------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "Neura-AI v1000 Hardcode"

OPENAI_KEY = os.getenv("OPENAI_API_KEY", None)
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "change_me_admin_token")  # set env var in prod
NEURA_MODEL = os.getenv("NEURA_MODEL", "gpt-5-mini")  # default model
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Feature toggles
FEATURE_FLAGS = {
    "enable_gradio": os.getenv("ENABLE_GRADIO", "false").lower() == "true",
    "enable_tts": os.getenv("ENABLE_TTS", "false").lower() == "true",
    "enable_file_uploads": True,
    "safe_mode": os.getenv("NEURA_SAFE_MODE", "true").lower() == "true",
}

# Logging
LOG_FILE = os.path.join(PROJECT_ROOT, "neura_v1000.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("neura_v1000")

# -------------------------------
# Simple File Memory & Persistence
# -------------------------------
MEMORY_PATH = os.path.join(PROJECT_ROOT, "memory.json")
USAGE_PATH = os.path.join(PROJECT_ROOT, "usage.json")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_memory_lock = threading.Lock()
_usage_lock = threading.Lock()

def _ensure_memory():
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"conversations": {}}, f)

def _ensure_usage():
    if not os.path.exists(USAGE_PATH):
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump({"calls": []}, f)

_ensure_memory()
_ensure_usage()

def read_memory():
    with _memory_lock:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

def write_memory(data):
    with _memory_lock:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def append_usage(entry: Dict[str, Any]):
    with _usage_lock:
        try:
            with open(USAGE_PATH, "r", encoding="utf-8") as f:
                u = json.load(f)
        except Exception:
            u = {"calls": []}
        u["calls"].append(entry)
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(u, f, indent=2, ensure_ascii=False)

# -------------------------------
# Bot Engine
# -------------------------------

class BotEngine:
    def __init__(self,
                 model: str = NEURA_MODEL,
                 api_key: Optional[str] = OPENAI_KEY,
                 memory_path: str = MEMORY_PATH,
                 max_history: int = 30):
        self.model = model
        self.api_key = api_key
        self.memory_path = memory_path
        self.max_history = max_history
        if openai is None:
            logger.warning("openai package not found; BotEngine will fail on generate calls.")
        if api_key:
            try:
                openai.api_key = api_key
            except Exception:
                pass

    # internal memory helpers
    def _load(self):
        return read_memory()

    def _save(self, data):
        write_memory(data)

    def list_conversations(self) -> List[str]:
        data = self._load()
        return list(data.get("conversations", {}).keys())

    def get_conversation(self, convo_id: str) -> List[Dict[str, Any]]:
        data = self._load()
        return data.get("conversations", {}).get(convo_id, [])

    def append_message(self, convo_id: str, role: str, content: str):
        data = self._load()
        convos = data.setdefault("conversations", {})
        conv = convos.setdefault(convo_id, [])
        conv.append({"role": role, "content": content, "ts": int(time.time())})
        # cap conversation
        if len(conv) > self.max_history:
            conv[:] = conv[-self.max_history:]
        self._save(data)

    def clear_conversation(self, convo_id: str):
        data = self._load()
        convos = data.setdefault("conversations", {})
        convos[convo_id] = []
        self._save(data)

    def generate(self, user_text: str, convo_id: Optional[str] = None,
                 max_tokens: int = 300, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Wraps OpenAI ChatCompletion. Returns dict with keys:
        - answer: string or None
        - raw: raw response object
        - error: present if error
        - usage: usage info if available
        """
        if openai is None:
            return {"error": "OpenAI SDK not installed."}
        if not (self.api_key or os.getenv("OPENAI_API_KEY")):
            return {"error": "OpenAI API key not set (OPENAI_API_KEY env)."}
        # build messages
        messages = [{"role": "system", "content": self._system_prompt()}]
        if convo_id:
            history = self.get_conversation(convo_id)
            for m in history:
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            # call OpenAI ChatCompletion
            resp = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = ""
            try:
                choice = resp.choices[0]
                content = choice.message.get("content", "")
            except Exception:
                content = str(resp)
            # save to memory
            if convo_id:
                self.append_message(convo_id, "user", user_text)
                self.append_message(convo_id, "assistant", content)
            # log usage
            usage_info = getattr(resp, "usage", None)
            usage_entry = {
                "time": datetime.utcnow().isoformat() + "Z",
                "convo": convo_id or "none",
                "model": self.model,
                "prompt_len": sum(len(m.get("content","")) for m in messages),
                "usage": usage_info if usage_info else {},
            }
            append_usage(usage_entry)
            return {"answer": content, "raw": resp, "usage": usage_info}
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("OpenAI call failed")
            return {"error": str(e), "trace": tb}

    def _system_prompt(self):
        # dynamic system prompt for persona/mode
        base = ("You are Neura-AI v1000, a premium AI assistant optimized for accuracy, "
                "conciseness, and business-grade responses. Follow user instructions carefully.")
        if FEATURE_FLAGS.get("safe_mode"):
            base += " Do not produce disallowed content, and refuse unsafe requests."
        return base

# single shared engine instance
BOT = BotEngine()

# -------------------------------
# Rate limiting & simple auth
# -------------------------------
RATE_WINDOW = 10  # seconds
RATE_MAX = int(os.getenv("NEURA_RATE_MAX", "20"))
_rate_store: Dict[str, List[float]] = {}
_rate_lock = threading.Lock()

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        arr = _rate_store.setdefault(ip, [])
        # remove old
        window_start = now - RATE_WINDOW
        arr[:] = [t for t in arr if t >= window_start]
        if len(arr) >= RATE_MAX:
            return True
        arr.append(now)
        _rate_store[ip] = arr
    return False

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-ADMIN-TOKEN") or request.args.get("admin_token")
        if not token or token != ADMIN_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

# -------------------------------
# Background worker queue & scheduler
# -------------------------------
WORKER_QUEUE = queue.Queue()
WORKER_RUNNING = True

def worker_thread():
    while WORKER_RUNNING:
        try:
            task = WORKER_QUEUE.get(timeout=1)
        except queue.Empty:
            continue
        try:
            logger.info("Worker executing task: %s", getattr(task, "name", str(task)))
            task()
        except Exception:
            logger.exception("Worker task failed")
        finally:
            WORKER_QUEUE.task_done()

_worker = threading.Thread(target=worker_thread, daemon=True)
_worker.start()

def schedule_task(func, delay: float = 0):
    def task_wrapper():
        time.sleep(delay)
        try:
            func()
        except Exception:
            logger.exception("Scheduled task failed")
    WORKER_QUEUE.put(task_wrapper)

atexit.register(lambda: globals().update({"WORKER_RUNNING": False}))

# -------------------------------
# Small utilities
# -------------------------------
def make_id(prefix="c"):
    return prefix + "_" + uuid.uuid4().hex[:12]

def safe_text(t):
    if t is None:
        return ""
    return str(t)

# -------------------------------
# Flask App & Routes
# -------------------------------
app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{{ title }}</title>
  <style>
    /* Premium neon UI - compact */
    :root{
      --bg:#030313; --card:#0f1220; --accent:#00f0ff; --muted:#9aa3c7;
    }
    body{background:radial-gradient(circle at 10% 10%, #061022, #02020a); color:#dfe9ff; font-family:Inter,Segoe UI,Arial; padding: 24px;}
    .card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius:14px; padding:20px; width:760px; margin:12px auto; box-shadow: 0 10px 40px rgba(0,0,0,0.6);}
    h1{font-family: 'Orbitron', sans-serif; letter-spacing:1px; color:var(--accent); margin:0 0 8px 0;}
    .subtitle{color:var(--muted); margin:0 0 18px 0;}
    .row{display:flex; gap:8px;}
    input[type=text], textarea{flex:1; padding:12px; border-radius:10px; border:1px solid rgba(255,255,255,0.04); background:rgba(0,0,0,0.4); color:#fff;}
    button{padding:12px 18px; border-radius:10px; border:none; cursor:pointer; font-weight:700; background:linear-gradient(90deg, #00f0ff, #0057ff); color:#001;}
    .response{margin-top:14px; background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; min-height:80px; white-space:pre-wrap;}
    .meta{font-size:12px;color:var(--muted); margin-top:8px;}
    .small{font-size:12px;color:var(--muted);}
  </style>
</head>
<body>
  <div class="card">
    <h1>{{ title }}</h1>
    <p class="subtitle">{{ subtitle }}</p>

    <div>
      <div class="row">
        <input id="prompt" type="text" placeholder="Ask Neura anything... (press Enter or Send)" />
        <button id="send">Send</button>
      </div>
      <div style="display:flex; gap:8px; margin-top:8px;">
        <input id="convo" type="text" placeholder="conversation id (optional)" style="width:220px;"/>
        <select id="mode">
          <option value="default">Default</option>
          <option value="business">Business</option>
          <option value="creative">Creative</option>
          <option value="debug">Debug</option>
        </select>
        <button id="clear">Clear Memory</button>
      </div>
      <div id="response" class="response">Neura is ready. Tip: use short prompts for faster replies.</div>
      <div class="meta small">Model: <span id="model">{{ model }}</span> • Safe Mode: {{ safe_mode }}</div>
    </div>
  </div>

<script>
async function sendPrompt(){
  const prompt = document.getElementById("prompt").value;
  const convo = document.getElementById("convo").value || "default_convo";
  const mode = document.getElementById("mode").value || "default";
  if(!prompt) return;
  document.getElementById("response").innerText = "⏳ Processing...";
  try{
    const res = await fetch("/ask", {
      method:"POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({command:prompt, convo_id:convo, mode:mode})
    });
    const j = await res.json();
    if(j.error) document.getElementById("response").innerText = "Error: " + j.error;
    else document.getElementById("response").innerText = j.answer || JSON.stringify(j);
  }catch(e){
    document.getElementById("response").innerText = "Network error: " + e.toString();
  }
}

document.getElementById("send").addEventListener("click", sendPrompt);
document.getElementById("prompt").addEventListener("keypress", function(e){
  if(e.key === "Enter") sendPrompt();
});
document.getElementById("clear").addEventListener("click", async function(){
  const convo = document.getElementById("convo").value || "default_convo";
  const token = prompt("Admin token (for local use):");
  if(!token) return;
  const res = await fetch("/command", {
    method:"POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({action:"clear_memory", convo_id:convo, admin_token:token})
  });
  const j = await res.json();
  alert(JSON.stringify(j));
});
</script>
</body>
</html>
"""

# -------------------------------
# Flask endpoints
# -------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE,
                                  title=APP_NAME,
                                  subtitle="Premium AI assistant — local/offline capable. Keep keys secret.",
                                  model=BOT.model,
                                  safe_mode=FEATURE_FLAGS.get("safe_mode"))

@app.route("/health", methods=["GET"])
def health():
    info = {
        "status": "ok",
        "model": BOT.model,
        "openai_key_set": bool(OPENAI_KEY or os.getenv("OPENAI_API_KEY")),
        "time": datetime.utcnow().isoformat() + "Z",
        "features": FEATURE_FLAGS
    }
    return jsonify(info)

@app.route("/metrics", methods=["GET"])
@require_admin
def metrics():
    # return lightweight usage summary
    try:
        with open(USAGE_PATH, "r", encoding="utf-8") as f:
            usage = json.load(f)
    except Exception:
        usage = {"calls": []}
    return jsonify({
        "uptime": "unknown",
        "total_calls": len(usage.get("calls", [])),
        "recent": usage.get("calls", [])[-20:]
    })

@app.route("/ask", methods=["POST"])
def ask():
    if is_rate_limited(request.remote_addr or "anon"):
        return jsonify({"error": "rate_limited"}), 429

    body = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
    command = safe_text(body.get("command") or body.get("question") or "")
    convo_id = body.get("convo_id") or "default_convo"
    mode = body.get("mode") or "default"

    if not command:
        return jsonify({"error": "no command provided"}), 400

    # mode influences system prompt or temperature
    if mode == "business":
        BOT.set_persona = "You are a professional business assistant; concise, formal."
    elif mode == "creative":
        BOT.set_persona = "You are creative, playful, imaginative."
    elif mode == "debug":
        # more verbose
        pass

    # schedule a background metric log
    schedule_task(lambda: append_usage({"event": "ask_called", "time": datetime.utcnow().isoformat()+"Z", "convo": convo_id}), 0)

    # Respond synchronously via BotEngine
    res = BOT.generate(command, convo_id=convo_id)
    if "error" in res:
        return jsonify({"error": res["error"]}), 500
    return jsonify({"answer": res.get("answer", ""), "usage": res.get("usage", {})})

@app.route("/command", methods=["POST"])
def command():
    # admin-only actions allowed via admin token in JSON or header
    body = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
    action = body.get("action")
    token = request.headers.get("X-ADMIN-TOKEN") or body.get("admin_token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "admin_auth_failed"}), 401
    if not action:
        return jsonify({"error": "no action specified"}), 400

    try:
        if action == "clear_memory":
            convo_id = body.get("convo_id", "default_convo")
            BOT.clear_conversation(convo_id)
            return jsonify({"ok": True, "message": f"cleared {convo_id}"})
        elif action == "list_memory":
            return jsonify({"ok": True, "conversations": BOT.list_conversations()})
        elif action == "set_persona":
            persona = body.get("persona", "")
            if persona:
                # naive set (we store in system prompt)
                BOT.system_prompt = persona
                return jsonify({"ok": True, "message": "persona set"})
            return jsonify({"error": "no persona provided"}), 400
        elif action == "set_model":
            model = body.get("model", "")
            if model:
                BOT.model = model
                return jsonify({"ok": True, "message": f"model set to {model}"})
            return jsonify({"error": "no model provided"}), 400
        else:
            return jsonify({"error": f"unknown action {action}"}), 400
    except Exception as e:
        logger.exception("command failed")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

# -------------------------------
# Tooling endpoints (summarize, translate, code_helper, imagesuggest)
# -------------------------------
@app.route("/tools/summarize", methods=["POST"])
def tool_summarize():
    body = request.get_json(force=True, silent=True) or {}
    text = body.get("text", "")
    if not text:
        return jsonify({"error": "no text provided"}), 400
    prompt = f"Summarize the following text concisely:\n\n{text}"
    res = BOT.generate(prompt, convo_id=None, max_tokens=200)
    if "error" in res:
        return jsonify({"error": res["error"]}), 500
    return jsonify({"summary": res.get("answer")})

@app.route("/tools/translate", methods=["POST"])
def tool_translate():
    body = request.get_json(force=True, silent=True) or {}
    text = body.get("text", "")
    target = body.get("to", "en")
    if not text:
        return jsonify({"error": "no text provided"}), 400
    prompt = f"Translate the following text to {target}:\n\n{text}"
    res = BOT.generate(prompt, convo_id=None, max_tokens=300)
    if "error" in res:
        return jsonify({"error": res["error"]}), 500
    return jsonify({"translation": res.get("answer")})

@app.route("/tools/code_helper", methods=["POST"])
def tool_code_helper():
    body = request.get_json(force=True, silent=True) or {}
    snippet = body.get("snippet", "")
    task = body.get("task", "explain")
    if not snippet:
        return jsonify({"error": "no snippet provided"}), 400
    prompt = f"{task.capitalize()} this code:\n\n{snippet}\n\nProvide a clear answer."
    res = BOT.generate(prompt, convo_id=None, max_tokens=400)
    if "error" in res:
        return jsonify({"error": res["error"]}), 500
    return jsonify({"result": res.get("answer")})

@app.route("/tools/imagesuggest", methods=["POST"])
def tool_image_suggest():
    body = request.get_json(force=True, silent=True) or {}
    description = body.get("description", "")
    style = body.get("style", "cinematic")
    if not description:
        return jsonify({"error": "no description provided"}), 400
    prompt = f"Create a detailed image prompt for an image of: {description}. Style: {style}. Include composition, lighting, mood, color palette."
    res = BOT.generate(prompt, convo_id=None, max_tokens=300)
    if "error" in res:
        return jsonify({"error": res["error"]}), 500
    return jsonify({"prompt": res.get("answer")})

# -------------------------------
# File upload & parse
# -------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    if not FEATURE_FLAGS.get("enable_file_uploads"):
        return jsonify({"error": "uploads_disabled"}), 403
    if 'file' not in request.files:
        return jsonify({"error": "no file part"}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"error": "no selected file"}), 400
    fname = f"{int(time.time())}_{uuid.uuid4().hex}_{secure_filename(f.filename)}"
    path = os.path.join(UPLOAD_DIR, fname)
    f.save(path)
    # optional: schedule parse
    def parse_task():
        text = try_extract_text(path)
        # store as memory under file_<id>
        convo = f"file_{uuid.uuid4().hex[:8]}"
        BOT.append_message(convo, "system", f"Uploaded file parsed: {os.path.basename(path)}")
        BOT.append_message(convo, "assistant", text[:4000])
        logger.info("Parsed file saved to convo %s", convo)
    schedule_task(parse_task, delay=0.5)
    return jsonify({"ok": True, "path": path})

def secure_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", ".", "_", "-")).strip().replace(" ", "_")

def try_extract_text(path):
    # naive: return binary size and first bytes if can't parse
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in [".txt", ".md", ".py", ".json", ".csv"]:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        # for other types, return placeholder
        return f"[binary file {os.path.basename(path)} size={os.path.getsize(path)}]"
    except Exception as e:
        logger.exception("extract failed")
        return f"[error extracting file: {e}]"

# -------------------------------
# Small admin + debug utilities
# -------------------------------
@app.route("/admin/status", methods=["GET"])
@require_admin
def admin_status():
    return jsonify({
        "ok": True,
        "model": BOT.model,
        "openai_key_set": bool(BOT.api_key or os.getenv("OPENAI_API_KEY")),
        "memory_count": len(BOT.list_conversations()),
        "recent_memory": BOT.get_conversation("default_convo")[-10:]
    })

@app.route("/admin/logs", methods=["GET"])
@require_admin
def admin_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Helpers for large-file safety / quotas
# -------------------------------
def ensure_quota_ok():
    # naive placeholder for usage quota checks
    # implement with your billing API if needed
    return True

# -------------------------------
# Optional Gradio integration (runs only if gradio installed and enabled)
# -------------------------------
if gr is not None and FEATURE_FLAGS.get("enable_gradio"):
    def gr_chat(message):
        r = BOT.generate(message, convo_id="gradio_default")
        return r.get("answer", r.get("error", "no response"))
    try:
        demo = gr.Interface(fn=gr_chat, inputs="text", outputs="text", title="Neura-AI v1000 (Gradio)")
        # Launch in background if needed - but in many hosts this won't work; keep commented
        # demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("GRADIO_PORT", 7860)), share=False)
    except Exception:
        logger.exception("Failed to init Gradio interface")

# -------------------------------
# Initialization tasks & sample data
# -------------------------------
def bootstrap_sample_data():
    # create a helpful welcome convo
    BOT.append_message("default_convo", "system", "Welcome to Neura-AI v1000. This conversation stores history.")
    BOT.append_message("default_convo", "assistant", "Ready to assist. Try: 'Summarize AI safety in one paragraph.'")

schedule_task(bootstrap_sample_data, delay=0.2)

# -------------------------------
# Run (WSGI-friendly)
# -------------------------------
def run_local():
    logger.info("Starting Neura-AI v1000 locally on %s:%s", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    run_local()