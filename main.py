import os
import sys
import json
import uuid
import time
import threading
import logging
import queue
import traceback
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# -------------------------------
# Configuration
# -------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "Neura-AI v1000 Hardcode"

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "change_me_admin_token")
NEURA_MODEL = os.getenv("NEURA_MODEL", "gpt-5-mini")
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")

FEATURE_FLAGS = {
    "safe_mode": os.getenv("NEURA_SAFE_MODE", "true").lower() == "true",
    "enable_file_uploads": True,
}

MEMORY_PATH = os.path.join(PROJECT_ROOT, "memory.json")
USAGE_PATH = os.path.join(PROJECT_ROOT, "usage.json")

os.makedirs(os.path.join(PROJECT_ROOT, "uploads"), exist_ok=True)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("neura_v1000")

# -------------------------------
# Memory helpers
# -------------------------------
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
        except:
            u = {"calls": []}
        u["calls"].append(entry)
        with open(USAGE_PATH, "w") as f:
            json.dump(u, f, indent=2, ensure_ascii=False)

# -------------------------------
# Bot Engine (new OpenAI SDK)
# -------------------------------
class BotEngine:
    def __init__(self, model=NEURA_MODEL, api_key=OPENAI_KEY, max_history=30):
        self.model = model
        self.api_key = api_key
        self.max_history = max_history
        if OpenAI:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("OpenAI SDK not found; BotEngine will fail on generate calls.")

    def list_conversations(self):
        return list(read_memory().get("conversations", {}).keys())

    def get_conversation(self, convo_id):
        return read_memory().get("conversations", {}).get(convo_id, [])

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

    def generate(self, user_text, convo_id=None, max_tokens=300, temperature=0.2):
        if not self.client:
            return {"error": "OpenAI SDK not installed."}
        if not self.api_key:
            return {"error": "OpenAI API key not set."}

        messages = [{"role": "system", "content": self._system_prompt()}]
        if convo_id:
            for m in self.get_conversation(convo_id):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = resp.choices[0].message.content

            if convo_id:
                self.append_message(convo_id, "user", user_text)
                self.append_message(convo_id, "assistant", content)

            usage_entry = {
                "time": datetime.utcnow().isoformat() + "Z",
                "convo": convo_id or "none",
                "model": self.model,
                "prompt_len": sum(len(m["content"]) for m in messages),
            }
            append_usage(usage_entry)
            return {"answer": content, "raw": resp}
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("OpenAI call failed")
            return {"error": str(e), "trace": tb}

    def _system_prompt(self):
        base = "You are Neura-AI v1000, a premium AI assistant optimized for accuracy and business-grade responses."
        if FEATURE_FLAGS.get("safe_mode"):
            base += " Do not produce disallowed content."
        return base

# -------------------------------
# Shared bot
# -------------------------------
BOT = BotEngine()

# -------------------------------
# Flask app
# -------------------------------
app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "Neura-AI ready"})

@app.route("/ask", methods=["POST"])
def ask():
    body = request.get_json(force=True) or {}
    prompt = body.get("command") or ""
    convo = body.get("convo_id") or "default_convo"
    if not prompt:
        return jsonify({"error": "no command provided"}), 400
    res = BOT.generate(prompt, convo_id=convo)
    return jsonify(res)

@app.route("/command", methods=["POST"])
def command():
    body = request.get_json(force=True) or {}
    token = body.get("admin_token")
    action = body.get("action")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    if action == "clear_memory":
        convo = body.get("convo_id", "default_convo")
        BOT.clear_conversation(convo)
        return jsonify({"ok": True, "message": f"cleared {convo}"})
    return jsonify({"error": "unknown action"}), 400

# -------------------------------
# Run app
# -------------------------------
def run_local():
    logger.info(f"Starting {APP_NAME} on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    run_local()