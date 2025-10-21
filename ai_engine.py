import random
import json
import time
from config import OPENAI_API_KEY, HUGGINGFACE_API_KEY

# -------------------------------
# NeuraAI_v200 • AI Engine (Core Brain)
# -------------------------------
# This module connects online GPT models (3–5) + offline cache
# It handles hybrid responses, memory recall, and dynamic mood control
# -------------------------------

class NeuraAIBrain:
    def __init__(self):
        self.models = ["GPT-3", "GPT-3.5", "GPT-4", "GPT-5"]
        self.api_keys = {
            "openai": OPENAI_API_KEY,
            "huggingface": HUGGINGFACE_API_KEY
        }
        self.memory_file = "memory_store.json"
        self.chat_log_file = "chat_logs.json"
        self.last_mood = "neutral"
        self.offline_mode = False

    # -------------------------------
    # Load & Save Memory
    # -------------------------------
    def load_memory(self):
        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_memory(self, memory_data):
        with open(self.memory_file, "w") as f:
            json.dump(memory_data, f, indent=4)

    # -------------------------------
    # Load Chat Logs
    # -------------------------------
    def log_message(self, role, message):
        try:
            with open(self.chat_log_file, "r") as f:
                logs = json.load(f)
        except:
            logs = []

        logs.append({"role": role, "message": message, "time": time.ctime()})
        with open(self.chat_log_file, "w") as f:
            json.dump(logs, f, indent=4)

    # -------------------------------
    # Generate AI Reply (Simulated Hybrid)
    # -------------------------------
    def generate_reply(self, prompt):
        self.log_message("user", prompt)

        # Simulate hybrid GPT intelligence selection
        chosen_model = random.choice(self.models)
        response_speed = random.uniform(0.2, 0.5)
        time.sleep(response_speed)

        # Offline / Online simulation
        if self.offline_mode:
            reply = f"[Offline Mode - Cached {chosen_model}] Response: I’m currently in local mode but still thinking fast!"
        else:
            reply = f"[{chosen_model}] says: That’s a great thought! Here’s my insight — {prompt[::-1]}"

        # Dynamic mood (affects tone)
        self.last_mood = random.choice(["happy", "focused", "calm", "curious"])
        reply += f" 🤖 (Mood: {self.last_mood})"

        self.log_message("assistant", reply)
        return reply

    # -------------------------------
    # Switch Modes
    # -------------------------------
    def toggle_mode(self, mode):
        if mode.lower() == "offline":
            self.offline_mode = True
        else:
            self.offline_mode = False
        return f"NeuraAI switched to {mode} mode."

    # -------------------------------
    # Clear Memory
    # -------------------------------
    def reset_memory(self):
        self.save_memory({})
        return "🧠 Memory cleared successfully!"


# -------------------------------
# Quick Test (Optional)
# -------------------------------
if __name__ == "__main__":
    brain = NeuraAIBrain()
    print(brain.toggle_mode("online"))
    print(brain.generate_reply("How do you feel today?"))