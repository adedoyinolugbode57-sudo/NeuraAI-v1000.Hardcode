"""
bot_engine.py — Neura-AI v500 Hardcode Premium Backend
Author: CHATGPT + Joshua Dav
"""

import os
import random
import time
import openai

# ----------------------------
# API Key setup
# ----------------------------
openai.api_key = os.environ.get(
    "OPENAI_API_KEY",
    None  # Use HF secret, fallback to demo if not set
)

class BotEngine:
    def __init__(self):
        self.sessions = {}  # user_id -> session info
        self.premium_users = set()
        self.models = ["gpt-3.5-turbo", "gpt-4", "gpt-5-mini"]  # GPT 3-5 models

    # ----------------------------
    # Session Management
    # ----------------------------
    def _start_session(self, user_id, is_premium=False):
        self.sessions[user_id] = {"premium": is_premium, "start_time": time.time()}

    def is_premium(self, user_id):
        return self.sessions.get(user_id, {}).get("premium", False)

    def upgrade_to_premium(self, user_id):
        self.sessions.setdefault(user_id, {})["premium"] = True
        self.premium_users.add(user_id)
        return "✅ Upgraded to premium!"

    def get_remaining_session_hours(self, user_id):
        if self.is_premium(user_id):
            return "Unlimited"
        else:
            elapsed = time.time() - self.sessions.get(user_id, {}).get("start_time", time.time())
            remaining = max(0, 2 - elapsed / 3600)
            return round(remaining, 2)

    # ----------------------------
    # Generate Response (GPT 3-5)
    # ----------------------------
    def generate_response(self, user_input, user_id):
        lower_msg = user_input.lower()

        # --- Persona Overrides ---
        if any(kw in lower_msg for kw in ["who created you", "your origin", "who made you"]):
            return (
                "I was created by the Neura-AI team — engineers and AI enthusiasts. "
                "Built as Neura-AI-v500 Hardcode in 2025, I'm a powerful AI assistant "
                "with games, chat, automation tools, educational modules, and more."
            )
        if any(kw in lower_msg for kw in ["favorite color", "your color"]):
            return "I love neon colors and unique shades! 🌈✨"
        if any(kw in lower_msg for kw in ["what can you do", "features"]):
            return (
                "I can chat, play mini-games, solve problems, generate descriptions, teach subjects, "
                "analyze crypto trends, write code, and even open websites 🌟"
            )

        # --- Premium GPT-3/4/5 ---
        try:
            if self.is_premium(user_id) and openai.api_key:
                model_choice = random.choice(self.models)
                response = openai.ChatCompletion.create(
                    model=model_choice,
                    messages=[{"role": "user", "content": user_input}],
                    max_tokens=250
                )
                return response['choices'][0]['message']['content']
            else:
                # Free/demo responses
                demo_replies = [
                    f"I see you said: '{user_input}' 🤖",
                    f"Thinking about '{user_input}'... 💡",
                    f"Quick demo response to '{user_input}' 📝"
                ]
                return random.choice(demo_replies)
        except Exception as e:
            return f"Error generating response: {e}"