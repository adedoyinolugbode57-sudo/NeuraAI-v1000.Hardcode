"""
Neura-AI v1000 Premium - main.py
Features:
- Full BotEngine: memory, conversation history, system prompts, persona modes
- Flask web app with neon UI and conversation support
- Admin endpoints: logs, memory listing, clear memory, set persona/model
- Rate limiting & usage logging
- File uploads & parsing
- Tool endpoints: summarize, translate, code helper, image suggestions
- Background worker queue & scheduler
- Optional Gradio integration
- Feature flags: safe mode, TTS, Gradio toggle
- Initialization: welcome conversation
- Environment variable support for OPENAI_API_KEY
"""

import os, sys, time, json, uuid, queue, threading, traceback, base64
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# --- Optional imports ---
try: import openai
except: openai = None
try: import gradio as gr
except: gr = None

# --- Configuration ---
APP_NAME = "Neura-AI Premium v1000"
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "admin123")
MODEL = os.getenv("NEURA_MODEL", "gpt-5-mini")

FEATURE_FLAGS = {
    "safe_mode": os.getenv("NEURA_SAFE_MODE", "true").lower() == "true",
    "enable_file_uploads": True,
    "enable_gradio": os.getenv("ENABLE_GRADIO", "false").lower() == "true",
    "enable_tts": os.getenv("ENABLE_TTS", "false").lower() == "true",
}

# --- Logging ---
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neura_v1000")

# --- Paths ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(PROJECT_ROOT, "memory.json")
USAGE_PATH = os.path.join(PROJECT_ROOT, "usage.json")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_memory_lock = threading.Lock()
_usage_lock = threading.Lock()

def _ensure_memory():
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w") as f:
            json.dump({"conversations": {}}, f)
def _ensure_usage():
    if not os.path.exists(USAGE_PATH):
        with open(USAGE_PATH, "w") as f:
            json.dump({"calls": []}, f)
_ensure_memory(); _ensure_usage()

def read_memory():
    with _memory_lock:
        with open(MEMORY_PATH, "r") as f: return json.load(f)
def write_memory(data):
    with _memory_lock:
        with open(MEMORY_PATH, "w") as f: json.dump(data, f, indent=2)
def append_usage(entry):
    with _usage_lock:
        try: u = json.load(open(USAGE_PATH))
        except: u={"calls":[]}
        u["calls"].append(entry)
        with open(USAGE_PATH,"w") as f: json.dump(u,f,indent=2)

# --- BotEngine ---
class BotEngine:
    def __init__(self, model=MODEL, api_key=OPENAI_KEY, max_history=30):
        self.model = model
        self.api_key = api_key
        self.max_history = max_history
        self.system_prompt = "You are Neura-AI Premium, optimized for accuracy and safety."
        if FEATURE_FLAGS.get("safe_mode"):
            self.system_prompt += " Do not produce unsafe content."
        if openai and api_key: openai.api_key = api_key

    def _load(self): return read_memory()
    def _save(self, data): write_memory(data)
    def list_conversations(self):
        return list(self._load().get("conversations", {}).keys())
    def get_conversation(self, cid): return self._load().get("conversations", {}).get(cid, [])
    def append_message(self, cid, role, content):
        data = self._load()
        convos = data.setdefault("conversations", {})
        conv = convos.setdefault(cid, [])
        conv.append({"role": role, "content": content, "ts": int(time.time())})
        if len(conv) > self.max_history: conv[:] = conv[-self.max_history:]
        self._save(data)
    def clear_conversation(self, cid):
        data=self._load()
        data.setdefault("conversations", {})[cid] = []
        self._save(data)

    def generate(self, user_text, cid=None, max_tokens=300, temperature=0.2):
        if openai is None: return {"error":"OpenAI SDK not installed."}
        if not (self.api_key or os.getenv("OPENAI_API_KEY")):
            return {"error":"API key not set."}
        messages = [{"role":"system","content":self.system_prompt}]
        if cid:
            for m in self.get_conversation(cid):
                messages.append({"role":m["role"],"content":m["content"]})
        messages.append({"role":"user","content":user_text})
        try:
            resp=openai.ChatCompletion.create(model=self.model, messages=messages,
                                             max_tokens=max_tokens, temperature=temperature)
            content = resp.choices[0].message.get("content","") if resp.choices else str(resp)
            if cid: self.append_message(cid,"user",user_text); self.append_message(cid,"assistant",content)
            append_usage({"time":datetime.utcnow().isoformat()+"Z","convo":cid or "none","model":self.model})
            return {"answer": content, "raw": resp}
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("OpenAI call failed")
            return {"error": str(e), "trace": tb}

BOT = BotEngine()

# --- Rate limiting ---
RATE_WINDOW, RATE_MAX = 10, 20
_rate_store, _rate_lock = {}, threading.Lock()
def is_rate_limited(ip):
    now=time.time()
    with _rate_lock:
        arr = _rate_store.setdefault(ip, [])
        arr[:] = [t for t in arr if t>=now-RATE_WINDOW]
        if len(arr) >= RATE_MAX: return True
        arr.append(now); _rate_store[ip] = arr
    return False

# --- Admin auth ---
def require_admin(f):
    @wraps(f)
    def wrapper(*a, **kw):
        token = request.headers.get("X-ADMIN-TOKEN") or request.args.get("admin_token")
        if token != ADMIN_TOKEN: return jsonify({"error":"unauthorized"}),401
        return f(*a,**kw)
    return wrapper

# --- Background worker queue ---
WORKER_QUEUE = queue.Queue()
WORKER_RUNNING=True
def worker_thread():
    while WORKER_RUNNING:
        try: task = WORKER_QUEUE.get(timeout=1)
        except queue.Empty: continue
        try: task()
        except: logger.exception("Worker task failed")
        finally: WORKER_QUEUE.task_done()
_worker = threading.Thread(target=worker_thread, daemon=True); _worker.start()
def schedule_task(func, delay=0): WORKER_QUEUE.put(lambda: (time.sleep(delay), func()))

# --- Utilities ---
def make_id(prefix="c"): return prefix+"_"+uuid.uuid4().hex[:12]
def safe_text(t): return str(t) if t is not None else ""
def secure_filename(name): return "".join(c for c in name if c.isalnum() or c in (" ",".","_","-")).strip().replace(" ","_")

# --- Flask app ---
app = Flask(__name__); CORS(app)
HTML_TEMPLATE = """
<!doctype html>
<html>
<head><meta charset="utf-8"/><title>{{title}}</title></head>
<body>
<h1>{{title}}</h1>
<input id="prompt" placeholder="Ask Neura..."/><button onclick="send()">Send</button>
<pre id="resp"></pre>
<script>
async function send(){
var p=document.getElementById("prompt").value;
var r=document.getElementById("resp");
r.innerText="⏳ Processing...";
var res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:p})});
var j=await res.json();
r.innerText=j.answer||j.error;}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index(): return render_template_string(HTML_TEMPLATE, title=APP_NAME)
@app.route("/health", methods=["GET"])
def health(): return jsonify({"status":"ok","model":BOT.model})

@app.route("/ask", methods=["POST"])
def ask():
    if is_rate_limited(request.remote_addr or "anon"): return jsonify({"error":"rate_limited"}),429
    body=request.get_json(force=True,silent=True) or {}
    command=safe_text(body.get("command",""))
    if not command: return jsonify({"error":"no command"}),400
    return jsonify(BOT.generate(command))

@app.route("/command", methods=["POST"])
@require_admin
def command():
    body=request.get_json(force=True,silent=True) or {}
    action=body.get("action")
    if action=="clear_memory":
        BOT.clear_conversation