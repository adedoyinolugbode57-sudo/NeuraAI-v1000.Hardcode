import os
import sys
import json
import time
import uuid
import logging
import threading
import queue
import traceback
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Optional OpenAI and Gradio
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
APP_NAME = "Neura-AI v1000 Hardcode"
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", None)
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "change_me")

FEATURE_FLAGS = {
    "enable_gradio": os.getenv("ENABLE_GRADIO", "false").lower() == "true",
    "safe_mode": os.getenv("NEURA_SAFE_MODE", "true").lower() == "true",
}

# -------------------------------
# Logging (Render-friendly)
# -------------------------------
logger = logging.getLogger("neura_v1000")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

# -------------------------------
# Memory / Usage
# -------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(PROJECT_ROOT, "memory.json")
USAGE_PATH = os.path.join(PROJECT_ROOT, "usage.json")
_memory_lock = threading.Lock()
_usage_lock = threading.Lock()

def _ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)

_ensure_file(MEMORY_PATH, {"conversations": {}})
_ensure_file(USAGE_PATH, {"calls": []})

def read_memory():
    with _memory_lock:
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)

def write_memory(data):
    with _memory_lock:
        with open(MEMORY_PATH, "w") as f:
            json.dump(data, f, indent=2)

def append_usage(entry):
    with _usage_lock:
        try:
            with open(USAGE_PATH, "r") as f:
                u = json.load(f)
        except Exception:
            u = {"calls": []}
        u["calls"].append(entry)
        with open(USAGE_PATH, "w") as f:
            json.dump(u, f, indent=2)

# -------------------------------
# Bot Engine
# -------------------------------
class BotEngine:
    def __init__(self, model="gpt-5-mini", max_history=30):
        self.model = model
        self.max_history = max_history

    def get_conversation(self, convo_id):
        data = read_memory()
        return data.get("conversations", {}).get(convo_id, [])

    def append_message(self, convo_id, role, content):
        data = read_memory()
        convos = data.setdefault("conversations", {})
        conv = convos.setdefault(convo_id, [])
        conv.append({"role": role, "content": content, "ts": int(time.time())})
        if len(conv) > self.max_history:
            conv[:] = conv[-self.max_history:]
        write_memory(data)

    def clear_conversation(self, convo_id):
        data = read_memory()
        convos = data.setdefault("conversations", {})
        convos[convo_id] = []
        write_memory(data)

    def generate(self, user_text, convo_id=None):
        # Minimal placeholder for testing
        answer = f"Echo: {user_text}"
        if convo_id:
            self.append_message(convo_id, "user", user_text)
            self.append_message(convo_id, "assistant", answer)
            append_usage({"time": datetime.utcnow().isoformat()+"Z", "convo": convo_id})
        return {"answer": answer}

BOT = BotEngine()

# -------------------------------
# Flask App
# -------------------------------
app = Flask(__name__)
CORS(app)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>{{title}}</title>
<style>
body{background:#030313;color:#dfe9ff;font-family:Arial;padding:20px;}
.card{background:#0f1220;padding:20px;border-radius:12px;max-width:600px;margin:auto;}
input,textarea{width:100%;padding:8px;margin:4px 0;}
button{padding:8px 16px;background:#00f0ff;border:none;color:#001;}
.response{margin-top:10px;background:#111;color:#fff;padding:10px;border-radius:8px;white-space:pre-wrap;}
</style>
</head>
<body>
<div class="card">
<h1>{{title}}</h1>
<input id="prompt" placeholder="Ask Neura..."/>
<button id="send">Send</button>
<div class="response" id="response">Neura ready!</div>
</div>
<script>
document.getElementById("send").onclick = async function(){
  const prompt=document.getElementById("prompt").value;
  if(!prompt)return;
  document.getElementById("response").innerText="⏳ Processing...";
  try{
    const res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:prompt})});
    const j=await res.json();
    document.getElementById("response").innerText=j.answer||j.error||"No response";
  }catch(e){document.getElementById("response").innerText="Network error: "+e;}
};
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, title=APP_NAME)

@app.route("/ask", methods=["POST"])
def ask():
    body = request.get_json(force=True) or {}
    cmd = body.get("command")
    if not cmd:
        return jsonify({"error": "no command provided"}), 400
    res = BOT.generate(cmd, convo_id="default")
    return jsonify(res)

@app.route("/command", methods=["POST"])
def command():
    body = request.get_json(force=True) or {}
    token = body.get("admin_token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    action = body.get("action")
    if action == "clear_memory":
        BOT.clear_conversation("default")
        return jsonify({"ok": True})
    return jsonify({"error": "unknown action"}), 400

# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    logger.info(f"Starting {APP_NAME} on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT)