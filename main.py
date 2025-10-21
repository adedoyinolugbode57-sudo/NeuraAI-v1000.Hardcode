"""
main.py — Ultra-Premium NeuraAI_v500 Hardcode
Author: CHATGPT + Joshua•Dav
"""

import os, json, time, random, webbrowser
from flask import Flask, request, jsonify
from flask_cors import CORS
import gradio as gr

# ----------------------------
# Modules
# ----------------------------
from bot_engine import BotEngine
from voice_engine import VoiceBot
from mini_games import random_game
from automation import AutomationEngine

# ----------------------------
# Initialize App & Engines
# ----------------------------
app = Flask(__name__)
CORS(app)

bot = BotEngine()
voice_bot_female = VoiceBot(gender="female", rate=160)
voice_bot_male = VoiceBot(gender="male", rate=140)
automation_engine = AutomationEngine()

# ----------------------------
# Helper Functions
# ----------------------------
def get_user_id(req):
    return req.args.get("user_id", "local_user")

def log_chat(user_id, role, msg):
    path = "chat_logs.json"
    logs = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            logs = json.load(f)
    if user_id not in logs:
        logs[user_id] = []
    logs[user_id].append({"role": role, "msg": msg, "timestamp": time.time()})
    with open(path, "w") as f:
        json.dump(logs, f, indent=2)

def get_random_emoji():
    return f"emoji_{random.randint(1,500):03}.png"

def fetch_crypto_insight(symbol="BTC"):
    # Placeholder: integrate crypto API for real-time info
    dummy_data = {"symbol": symbol, "price": random.uniform(20000, 40000), "change_24h": random.uniform(-10, 10)}
    return dummy_data

def solve_problem(problem_text):
    # Placeholder for problem solving logic
    solution = f"Solved: {problem_text[:50]}..."
    return solution

def write_description(topic):
    # Placeholder for automated description writer
    desc = f"Premium AI description for {topic}:\nThis is a detailed explanation with examples, insights, and practical use."
    return desc

def educational_explain(subject):
    # Placeholder for education tab logic
    return f"Educational breakdown for {subject}:\nStep-by-step explanation with examples."

# ----------------------------
# Flask Endpoints
# ----------------------------
@app.route("/chat", methods=["GET"])
def chat():
    user_input = request.args.get("msg", "")
    user_id = get_user_id(request)
    premium_flag = request.args.get("premium", "false").lower() == "true"
    voice_mode = request.args.get("voice", "false").lower() == "true"

    bot._start_session(user_id=user_id, is_premium=premium_flag)
    reply = bot.generate_response(user_input, user_id=user_id)

    log_chat(user_id, "user", user_input)
    log_chat(user_id, "bot", reply)

    if voice_mode:
        if premium_flag:
            voice_bot_female.speak(reply)
        else:
            voice_bot_male.speak(reply)

    remaining_hours = bot.get_remaining_session_hours(user_id=user_id)
    emoji_file = get_random_emoji()

    return jsonify({
        "reply": reply,
        "emoji": emoji_file,
        "remaining_hours": remaining_hours
    })

@app.route("/upgrade", methods=["POST"])
def upgrade():
    user_id = get_user_id(request)
    msg = bot.upgrade_to_premium(user_id)
    remaining_hours = bot.get_remaining_session_hours(user_id)
    return jsonify({"message": msg, "remaining_hours": remaining_hours})

@app.route("/mini_game", methods=["GET"])
def mini_game():
    game = random_game()
    return jsonify({"game": game})

@app.route("/automation", methods=["POST"])
def automation():
    task_name = request.json.get("task")
    if hasattr(automation_engine, task_name):
        getattr(automation_engine, task_name)()
        return jsonify({"message": f"Automation '{task_name}' executed"})
    return jsonify({"message": "Task not found"}), 404

@app.route("/memory_store", methods=["GET"])
def memory_store():
    mem_path = "memory_store.json"
    if os.path.exists(mem_path):
        with open(mem_path, "r") as f:
            memory = json.load(f)
        return jsonify(memory)
    return jsonify({})

@app.route("/session_info", methods=["GET"])
def session_info():
    user_id = get_user_id(request)
    return jsonify({
        "remaining_hours": bot.get_remaining_session_hours(user_id),
        "is_premium": bot.is_premium(user_id)
    })

@app.route("/voice_list", methods=["GET"])
def voice_list():
    voices = {
        "female": ["Siri","Eva","Clara","Luna","Nova","Mia","Aria","Zara","Lily","Sophia"],
        "male": ["Alex","John","Leo","Ethan","Max","Ryan","Oliver","Jack","Noah","Liam"]
    }
    return jsonify(voices)

@app.route("/open_url", methods=["POST"])
def open_url():
    url = request.json.get("url")
    if url:
        webbrowser.open(url)
        return jsonify({"message": f"Opened {url}"})
    return jsonify({"message": "No URL provided"}), 400

@app.route("/crypto", methods=["GET"])
def crypto_tab():
    symbol = request.args.get("symbol", "BTC")
    data = fetch_crypto_insight(symbol)
    return jsonify(data)

@app.route("/education", methods=["GET"])
def education_tab():
    subject = request.args.get("subject", "Mathematics")
    explanation = educational_explain(subject)
    return jsonify({"subject": subject, "explanation": explanation})

@app.route("/problem_solver", methods=["POST"])
def problem_solver_tab():
    problem_text = request.json.get("problem")
    solution = solve_problem(problem_text)
    return jsonify({"solution": solution})

@app.route("/description_writer", methods=["POST"])
def description_writer_tab():
    topic = request.json.get("topic")
    desc = write_description(topic)
    return jsonify({"description": desc})

# ----------------------------
# Gradio Interface
# ----------------------------
def gr_interface(user_input, user_id="local_user", premium=False, voice=False, color="#00FF00"):
    bot._start_session(user_id=user_id, is_premium=premium)
    reply = bot.generate_response(user_input, user_id=user_id)
    log_chat(user_id, "user", user_input)
    log_chat(user_id, "bot", reply)
    
    if voice:
        if premium:
            voice_bot_female.speak(reply)
        else:
            voice_bot_male.speak(reply)
    
    emoji_file = get_random_emoji()
    return reply, emoji_file

with gr.Blocks() as demo:
    gr.Markdown("# Neura-AI v500 Hardcode 🤖💎")
    with gr.Row():
        txt_input = gr.Textbox(label="Type your message here")
        output_txt = gr.Textbox(label="AI Reply")
        emoji_img = gr.Image(label="Random Emoji")
    with gr.Row():
        btn_submit = gr.Button("Send")
        color_picker = gr.ColorPicker(label="Pick UI Color", value="#00FF00")
        voice_checkbox = gr.Checkbox(label="Voice Mode", value=False)
        premium_checkbox = gr.Checkbox(label="Premium", value=False)
    btn_submit.click(fn=gr_interface, inputs=[txt_input, gr.Textbox(value="local_user", visible=False), premium_checkbox, voice_checkbox, color_picker], outputs=[output_txt, emoji_img])

# ----------------------------
# Run Flask + Gradio
# ----------------------------
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: demo.launch(server_name="0.0.0.0", server_port=7860, share=False)).start()
    app.run(host="0.0.0.0", port=5000, debug=True)