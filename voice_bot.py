"""
voice_bot.py — Full Voice-enabled Assistant for NeuraAI v200 Hardcode
- Integrates BotEngine + VoiceEngine
- Handles user input (text or speech)
- Supports personas, voice gender, and polite/friendly styles
- Offline fallback supported
"""

import threading
import queue
import time
try:
    from bot_engine import BotEngine
except Exception:
    BotEngine = None

try:
    from voice_engine import VoiceEngine
except Exception:
    VoiceEngine = None

class VoiceBot:
    def __init__(self, persona="friendly", voice_gender="female", enable_voice=True):
        # Initialize BotEngine
        self.bot = BotEngine(persona=persona, enable_voice=enable_voice)
        self.enable_voice = enable_voice and (VoiceEngine is not None)
        # Initialize VoiceEngine
        if self.enable_voice:
            self.voice = VoiceEngine(prefer_online=False)
            self.voice.set_voice(voice_gender)
        else:
            self.voice = None
        self.persona = persona
        self.voice_gender = voice_gender

    # ----------------------------
    # Change persona / voice
    # ----------------------------
    def set_persona(self, persona: str):
        self.persona = persona
        if self.bot:
            self.bot.set_persona(persona)

    def set_voice_gender(self, gender: str):
        self.voice_gender = gender
        if self.voice:
            self.voice.set_voice(gender)

    # ----------------------------
    # Speak wrapper (non-blocking)
    # ----------------------------
    def speak(self, text: str):
        if self.enable_voice and self.voice:
            try:
                self.voice.speak(text)
            except Exception:
                pass

    # ----------------------------
    # Generate response
    # ----------------------------
    def respond(self, user_input: str, user_id="local_user", is_premium=False, online=True):
        """
        Main interaction: returns AI response text & speaks it
        """
        if self.bot:
            reply = self.bot.generate_response(
                user_input=user_input,
                user_id=user_id,
                is_premium=is_premium,
                online=online
            )
            return reply
        return "Bot engine not initialized."

    # ----------------------------
    # Simple interaction loop
    # ----------------------------
    def chat_loop(self):
        print("🎤 VoiceBot Ready! Type 'exit' to quit.\n")
        while True:
            user_input = input("You: ")
            if user_input.lower() in ("exit", "quit"):
                print("Exiting VoiceBot...")
                break
            reply = self.respond(user_input)
            print("Bot:", reply)

    # ----------------------------
    # Introduce assistant
    # ----------------------------
    def introduce(self):
        intro = f"Hello! I am your NeuraAI v200 assistant ({self.persona} persona, {self.voice_gender} voice)."
        print(intro)
        self.speak(intro)

# ----------------------------
# Quick test
# ----------------------------
if __name__ == "__main__":
    vb = VoiceBot(persona="friendly", voice_gender="female", enable_voice=True)
    vb.introduce()
    vb.chat_loop()