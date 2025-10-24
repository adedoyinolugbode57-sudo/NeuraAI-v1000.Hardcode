import os, sys, time, json, uuid, threading, queue, logging, traceback
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Optional OpenAI & Gradio
try: import openai
except: openai = None
try: import gradio as gr
except: gr = None

# ------------------------
# Configuration / Env
# ------------------------
APP_NAME = "Neura-AI v1000 Hardcode"
OPENAI_KEY = os.getenv("OPENAI_API_KEY", None)
ADMIN_TOKEN = os.getenv("NEURA_ADMIN_TOKEN", "change_me_admin_token")
NEURA_MODEL = os.getenv("NEURA_MODEL", "gpt-5-mini")
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

FEATURE_FLAGS = {
    "enable_gradio": os.getenv("ENABLE_GRADIO","false").lower()=="true",
    "safe_mode": os.getenv("NEURA_SAFE_MODE","true").lower()=="true",
    "enable_file_uploads": True,
}

# Logging
LOG_FILE = "neura_v1000.log"
logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("neura_v1000")

# Memory & Usage
MEMORY_PATH = "memory.json"
USAGE_PATH = "usage.json"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

_memory_lock = threading.Lock()
_usage_lock = threading.Lock()
def _ensure_file(path, default):
    if not os.path.exists(path):
        with open(path,"w") as f: json.dump(default,f)
_ensure_file(MEMORY_PATH, {"conversations":{}})
_ensure_file(USAGE_PATH, {"calls":[]})

def read_memory(): 
    with _memory_lock: return json.load(open(MEMORY_PATH,"r",encoding="utf-8"))
def write_memory(data):
    with _memory_lock: json.dump(data, open(MEMORY_PATH,"w",encoding="utf-8"), indent=2)
def append_usage(entry):
    with _usage_lock:
        try: u=json.load(open(USAGE_PATH,"r")); u["calls"].append(entry)
        except: u={"calls":[entry]}
        json.dump(u, open(USAGE_PATH,"w"), indent=2)

# ------------------------
# Bot Engine
# ------------------------
class BotEngine:
    def __init__(self, model=NEURA_MODEL, api_key=OPENAI_KEY, max_history=30):
        self.model = model
        self.api_key = api_key
        self.max_history = max_history
        if openai and api_key: openai.api_key = api_key
    def _load(self): return read_memory()
    def _save(self, data): write_memory(data)
    def list_conversations(self): return list(self._load().get("conversations",{}).keys())
    def get_conversation(self, cid): return self._load().get("conversations",{}).get(cid,[])
    def append_message(self, cid, role, content):
        data = self._load()
        convos = data.setdefault("conversations",{})
        conv = convos.setdefault(cid,[])
        conv.append({"role":role,"content":content,"ts":int(time.time())})
        if len(conv)>self.max_history: conv[:] = conv[-self.max_history:]
        self._save(data)
    def clear_conversation(self,cid): data=self._load(); data.setdefault("conversations",{})[cid]=[]; self._save(data)
    def generate(self, text, convo_id=None, max_tokens=300, temperature=0.2):
        if openai is None: return {"error":"OpenAI SDK not installed."}
        if not (self.api_key or os.getenv("OPENAI_API_KEY")): return {"error":"OpenAI key not set"}
        messages=[{"role":"system","content":self._system_prompt()}]
        if convo_id: 
            for m in self.get_conversation(convo_id): messages.append({"role":m["role"],"content":m["content"]})
        messages.append({"role":"user","content":text})
        try:
            resp=openai.ChatCompletion.create(model=self.model,messages=messages,max_tokens=max_tokens,temperature=temperature)
            content=resp.choices[0].message.get("content","") if hasattr(resp,"choices") else str(resp)
            if convo_id: self.append_message(convo_id,"user",text); self.append_message(convo_id,"assistant",content)
            usage_entry={"time":datetime.utcnow().isoformat()+"Z","convo":convo_id or "none","model":self.model}
            append_usage(usage_entry)
            return {"answer":content,"raw":resp}
        except Exception as e: tb=traceback.format_exc(); logger.exception("OpenAI call failed"); return {"error":str(e),"trace":tb}
    def _system_prompt(self):
        base="You are Neura-AI v1000, optimized for accuracy, conciseness."
        if FEATURE_FLAGS.get("safe_mode"): base+=" Refuse unsafe requests."
        return base

BOT=BotEngine()

# ------------------------
# Rate limiting & auth
# ------------------------
RATE_WINDOW, RATE_MAX = 10, 20
_rate_store,_rate_lock={},threading.Lock()
def is_rate_limited(ip):
    now=time.time()
    with _rate_lock:
        arr=_rate_store.setdefault(ip,[])
        arr[:] = [t for t in arr if t>=now-RATE_WINDOW]
        if len(arr)>=RATE_MAX: return True
        arr.append(now); _rate_store[ip]=arr
    return False
def require_admin(f):
    @wraps(f)
    def wrapper(*args,**kwargs):
        token=request.headers.get("X-ADMIN-TOKEN") or request.args.get("admin_token")
        if token!=ADMIN_TOKEN: return jsonify({"error":"unauthorized"}),401
        return f(*args,**kwargs)
    return wrapper

# ------------------------
# Flask app & routes
# ------------------------
app=Flask(__name__)
CORS(app)

HTML_TEMPLATE="""
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{title}}</title>
<style>:root{--bg:#030313;--card:#0f1220;--accent:#00f0ff;--muted:#9aa3c7;}
body{background:radial-gradient(circle at 10% 10%, #061022,#02020a); color:#dfe9ff; font-family:Inter,Segoe UI,Arial; padding:24px;}
.card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius:14px; padding:20px; width:760px; margin:12px auto; box-shadow:0 10px 40px rgba(0,0,0,0.6);}
h1{font-family:'Orbitron',sans-serif; letter-spacing:1px; color:var(--accent); margin:0 0 8px 0;}
.subtitle{color:var(--muted); margin:0 0 18px 0;}
.row{display:flex; gap:8px;}
input[type=text], textarea{flex:1; padding:12px; border-radius:10px; border:1px solid rgba(255,255,255,0.04); background:rgba(0,0,0,0.4); color:#fff;}
button{padding:12px 18px; border-radius:10px; border:none; cursor:pointer; font-weight:700; background:linear-gradient(90deg, #00f0ff,#0057ff); color:#001;}
.response{margin-top:14px; background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; min-height:80px; white-space:pre-wrap;}
.meta{font-size:12px;color:var(--muted); margin-top:8px;}
.small{font-size:12px;color:var(--muted);}
</style></head>
<body>
<div class="card"><h1>{{title}}</h1><p class="subtitle">{{subtitle}}</p>
<div><div class="row"><input id="prompt" type="text" placeholder="Ask Neura..."/><button id="send">Send</button></div>
<div style="display:flex; gap:8px; margin-top:8px;"><input id="convo" type="text" placeholder="conversation id (optional)" style="width:220px;"/>
<button id="clear">Clear Memory</button></div>
<div id="response" class="response">Neura is ready.</div>
<div class="meta small">Model: <span id="model">{{model}}</span> • Safe Mode: {{safe_mode}}</div></div></div>
<script>
async function sendPrompt(){
const prompt=document.getElementById("prompt").value;
const convo=document.getElementById("convo").value||"default_convo";
if(!prompt) return;
document.getElementById("response").innerText="⏳ Processing...";
try{
const res=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:prompt,convo_id:convo})});
const j=await res.json();
document.getElementById("response").innerText