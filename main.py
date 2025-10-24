"""
Neura-AI v1000 - Premium Hardcode Main.py
Features:
- Flask web app with embedded premium neon UI
- Bot engine (chat, memory, persona, conversation history)
- Endpoints: /, /ask, /command, /health, /metrics, /upload
- Admin authentication via env NEURA_ADMIN_TOKEN
- Rate limiting, logging, usage tracking
- File-based memory (safe small-scale)
- Tools: summarize, translate, code_helper, imagesuggest
- Background worker queue
- Optional Gradio integration
- Safe OpenAI API usage
"""

import os
import sys
import time
import json
import uuid
import queue
import atexit
import logging
import threading
import traceback
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS

try:
    import openai
except ImportError:
    openai = None

try:
    import gradio as gr
except ImportError:
    gr = None

# -------------------------------
# Configuration
# -------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "Neura-AI v1000 Hardcode"

OPENAI_KEY = os.getenv("OPENAI_API_KEY", None)
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "change_me_admin_token")
NEURA_MODEL = os.getenv("NEURA_MODEL", "gpt-5-mini")
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")

FEATURE_FLAGS = {
    "enable_gradio": os.getenv("ENABLE_GRADIO", "false").lower() == "true",
    "enable_file_uploads": True,
    "safe_mode": os.getenv("NEURA_SAFE_MODE", "true").lower() == "true",
}

# Logging
LOG_FILE = os.path.join(PROJECT_ROOT, "neura_v1000.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("neura_v1000")

# -------------------------------
# Memory & Usage
# -------------------------------
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

_ensure_memory()
_ensure_usage()

def read_memory():
    with _memory_lock:
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)

def write_memory(data):
    with _memory_lock:
        with open(MEMORY_PATH, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def append_usage(entry):
    with _usage_lock:
        try:
            with open(USAGE_PATH, "r") as f:
                u = json.load(f)
        except Exception:
            u = {"calls": []}
        u["calls"].append(entry)
        with open(USAGE_PATH, "w") as f:
            json.dump(u, f, indent=2, ensure_ascii=False)

# -------------------------------
# Bot Engine
# -------------------------------
class BotEngine:
    def __init__(self, model=NEURA_MODEL, api_key=OPENAI_KEY, memory_path=MEMORY_PATH, max_history=30):
        self.model = model
        self.api_key = api_key
        self.memory_path = memory_path
        self.max_history = max_history
        if openai and api_key:
            openai.api_key = api_key

    def _load(self):
        return read_memory()

    def _save(self, data):
        write_memory(data)

    def list_conversations(self):
        data = self._load()
        return list(data.get("conversations", {}).keys())

    def get_conversation(self, convo_id):
        data = self._load()
        return data.get("conversations", {}).get(convo_id, [])

    def append_message(self, convo_id, role, content):
        data = self._load()
        convos = data.setdefault("conversations", {})
        conv = convos.setdefault(convo_id, [])
        conv.append({"role": role, "content": content, "ts": int(time.time())})
        if len(conv) > self.max_history:
            conv[:] = conv[-self.max_history:]
        self._save(data)

    def clear_conversation(self, convo_id):
        data = self._load()
        convos = data.setdefault("conversations", {})
        convos[convo_id] = []
        self._save(data)

    def generate(self, user_text, convo_id=None, max_tokens=300, temperature=0.2):
        if openai is None:
            return {"error": "OpenAI SDK not installed."}
        if not (self.api_key or os.getenv("OPENAI_API_KEY")):
            return {"error": "OpenAI API key not set."}
        messages = [{"role": "system", "content": self._system_prompt()}]
        if convo_id:
            history = self.get_conversation(convo_id)
            for m in history:
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
            usage_info = getattr(resp, "usage", None)
            append_usage({"time": datetime.utcnow().isoformat()+"Z", "convo": convo_id or "none", "model": self.model, "prompt_len": sum(len(m["content"]) for m in messages), "usage": usage_info or {}})
            return {"answer": content, "raw": resp, "usage": usage_info}
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("OpenAI call failed")
            return {"error": str(e), "trace": tb}

    def _system_prompt(self):
        base = "You are Neura-AI v1000, premium AI assistant optimized for accuracy, conciseness, and business-grade responses."
        if FEATURE_FLAGS.get("safe_mode"):
            base += " Do not produce unsafe content."
        return base

BOT = BotEngine()

# -------------------------------
# Flask app & routes
# -------------------------------
app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{ title }}</title>
<style>
body{background:#030313;color:#dfe9ff;font-family:Inter,Arial;padding:24px;}
.card{background:#0f1220;border-radius:14px;padding:20px;width:760px;margin:12px auto;box-shadow:0 10px 40px rgba(0,0,0,0.6);}
h1{color:#00f0ff;margin:0 0 8px 0;}
.response{margin-top:14px;background:rgba(255,255,255,0.02);padding:12px;border-radius:8px;min-height:80px;white-space:pre-wrap;}
</style>
</head>
<body>
<div class="card">
<h1>{{ title }}</h1>
<input id="prompt" type="text" placeholder="Ask Neura anything..."/>
<button id="send">Send</button>
<div id="response" class="response">Neura is ready.</div>
</div>
<script>
async function sendPrompt(){
  const prompt = document.getElementById("prompt").value;
  if(!prompt) return;
  document.getElementById("response").innerText="⏳ Processing...";
  const res = await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:prompt,convo_id:"default_convo"})});
  const j = await res.json();
  document.getElementById("response").innerText=j.answer||j.error||"no response";
}
document.getElementById("send").addEventListener("click",sendPrompt);
document.getElementById("prompt").addEventListener("keypress",e=>{if(e.key==="Enter")sendPrompt();});
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE, title=APP_NAME)

@app.route("/ask", methods=["POST"])
def ask():
    body = request.get_json(force=True) or {}
    command = body.get("command","")
    convo_id = body.get("convo_id","default_convo")
    if not command:
        return jsonify({"error":"no command"}),400
    res = BOT.generate(command, convo_id=convo_id)
    return jsonify(res)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok","model":BOT.model,"openai_key_set":bool(OPENAI_KEY)})

#