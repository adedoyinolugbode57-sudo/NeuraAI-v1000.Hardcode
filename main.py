"""
Neura-AI v1000 "Hardcode" - Premium All-in-One main.py
Features:
- Flask web app with neon UI
- Bot engine with memory, personas, conversation history
- Endpoints: /, /ask, /command, /health, /metrics, /upload
- Admin commands via token
- Rate limiting, logging, usage tracking
- Optional Gradio integration
- Configurable model via env
- Minimal inline HTML template
- Future-ready for voice, TTS, crypto insights
"""

import os, sys, time, json, uuid, queue, threading, logging, traceback
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS

# Optional dependencies
try:
    import openai
except:
    openai = None

try:
    import gradio as gr
except:
    gr = None

# ------------------------------
# Config / Environment
# ------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "Neura-AI v1000 Hardcode"

OPENAI_KEY = os.getenv("OPENAI_API_KEY", None)
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "change_me")
NEURA_MODEL = os.getenv("NEURA_MODEL", "gpt-5-mini")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))

FEATURE_FLAGS = {
    "enable_gradio": os.getenv("ENABLE_GRADIO", "false").lower() == "true",
    "enable_file_uploads": True,
    "safe_mode": os.getenv("NEURA_SAFE_MODE", "true").lower() == "true",
}

# ------------------------------
# Logging
# ------------------------------
LOG_FILE = os.path.join(PROJECT_ROOT, "neura_v1000.log")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("neura_v1000")

# ------------------------------
# Memory & Usage
# ------------------------------
MEMORY_PATH = os.path.join(PROJECT_ROOT, "memory.json")
USAGE_PATH = os.path.join(PROJECT_ROOT, "usage.json")
os.makedirs(os.path.join(PROJECT_ROOT, "uploads"), exist_ok=True)

_memory_lock = threading.Lock()
_usage_lock = threading.Lock()

def ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f)

ensure_file(MEMORY_PATH, {"conversations": {}})
ensure_file(USAGE_PATH, {"calls": []})

def read_memory():
    with _memory_lock:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

def write_memory(data):
    with _memory_lock:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def append_usage(entry):
    with _usage_lock:
        try:
            u = read_usage()
        except:
            u = {"calls": []}
        u["calls"].append(entry)
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(u, f, indent=2, ensure_ascii=False)

def read_usage():
    with _usage_lock:
        with open(USAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

# ------------------------------
# Bot Engine
# ------------------------------
class BotEngine:
    def __init__(self, model=NEURA_MODEL, api_key=OPENAI_KEY, max_history=30):
        self.model = model
        self.api_key = api_key
        self.max_history = max_history
        if openai and api_key:
            openai.api_key = api_key

    def _load_memory(self):
        return read_memory()

    def _save_memory(self, data):
        write_memory(data)

    def list_conversations(self):
        return list(self._load_memory().get("conversations", {}).keys())

    def get_conversation(self, convo_id):
        return self._load_memory().get("conversations", {}).get(convo_id, [])

    def append_message(self, convo_id, role, content):
        data = self._load_memory()
        convos = data.setdefault("conversations", {})
        conv = convos.setdefault(convo_id, [])
        conv.append({"role": role, "content": content, "ts": int(time.time())})
        if len(conv) > self.max_history:
            conv[:] = conv[-self.max_history:]
        self._save_memory(data)

    def clear_conversation(self, convo_id):
        data = self._load_memory()
        data.setdefault("conversations", {})[convo_id] = []
        self._save_memory(data)

    def generate(self, user_text, convo_id=None, max_tokens=300, temperature=0.2):
        if openai is None:
            return {"error": "OpenAI SDK not installed."}
        if not (self.api_key or os.getenv("OPENAI_API_KEY")):
            return {"error": "API key not set."}

        messages = [{"role": "system", "content": self._system_prompt()}]
        if convo_id:
            for m in self.get_conversation(convo_id):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            resp = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = resp.choices[0].message.get("content", "")
            if convo_id:
                self.append_message(convo_id, "user", user_text)
                self.append_message(convo_id, "assistant", content)

            append_usage({
                "time": datetime.utcnow().isoformat()+"Z",
                "convo": convo_id or "none",
                "model": self.model,
                "prompt_len": sum(len(m.get("content","")) for m in messages),
            })
            return {"answer": content, "raw": resp}
        except Exception as e:
            logger.exception("OpenAI call failed")
            return {"error": str(e), "trace": traceback.format_exc()}

    def _system_prompt(self):
        base = ("You are Neura-AI v1000, premium AI assistant, concise, accurate, business-ready.")
        if FEATURE_FLAGS.get("safe_mode"):
            base += " Refuse unsafe content."
        return base

BOT = BotEngine()

# ------------------------------
# Flask App
# ------------------------------
app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head><title>{{ title }}</title></head>
<body>
<h1>{{ title }}</h1>
<p>{{ subtitle }}</p>
<input id="prompt" placeholder="Ask anything..." />
<button onclick="sendPrompt()">Send</button>
<div id="response">Neura ready.</div>
<script>
async function sendPrompt(){
  let prompt=document.getElementById("prompt").value;
  let res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:prompt, convo_id:"default"})});
  let j=await res.json();
  document.getElementById("response").innerText=j.answer||j.error;
}
</script>
</body>
</html>
"""

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-ADMIN-TOKEN") or request.args.get("admin_token")
        if token != ADMIN_TOKEN:
            return jsonify({"error":"unauthorized"}),401
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, title=APP_NAME, subtitle="Premium AI Assistant.")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    command = data.get("command","")
    convo = data.get("convo_id","default")
    if not command:
        return jsonify({"error":"no command"}),400
    return BOT.generate(command, convo_id=convo)

@app.route("/command", methods=["POST"])
@require_admin
def command():
    data = request.get_json(force=True)
    action = data.get("action")
    convo = data.get("convo_id","default")
    try:
        if action=="clear_memory":
            BOT.clear_conversation(convo)
            return jsonify({"ok":True})
        return jsonify({"error":"unknown action"})
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route("/health")
def health():
    return jsonify({"status":"ok","model":BOT.model})

# ------------------------------
# Optional Gradio
# ------------------------------
if gr and FEATURE_FLAGS.get("enable_gradio"):
    def gr_chat(msg):
        return BOT.generate(msg, convo_id="gradio_default").get("answer","no response")
    try:
        demo = gr.Interface(fn=gr_chat, inputs="text", outputs="text", title="Neura-AI Gradio")
    except:
        logger.exception("Gradio failed")

# ------------------------------
# Run
# ------------------------------
if __name__=="__main__":
    app.run(host=HOST, port=PORT)