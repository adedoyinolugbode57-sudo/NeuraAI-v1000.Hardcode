"""
automation.py — Handles small/medium automation tasks for NeuraAI_v200
Author: CHATGPT + Joshua•Dav
"""

import random
import time

class AutomationEngine:
    def __init__(self, is_premium=False):
        self.is_premium = is_premium
        self.tasks = []

    def schedule_task(self, func, *args, **kwargs):
        """
        Schedule and execute a task immediately for now.
        In future, could be extended for delayed/background execution.
        """
        self.tasks.append((func, args, kwargs))
        func(*args, **kwargs)

    # ----------------------------
    # Example automation tasks
    # ----------------------------
    def print_random_number(self):
        number = random.randint(1, 100)
        print(f"Automation task executed: Random number = {number}")

    def print_current_time(self):
        print(f"Automation task executed: Current UTC time = {time.strftime('%Y-%m-%d %H:%M:%S')}")

    def simple_countdown(self, seconds=5):
        print(f"Automation task: Countdown from {seconds}")
        for i in range(seconds, 0, -1):
            print(i)
            time.sleep(0.5)
        print("Countdown completed!")

    def show_motivation(self):
        quotes = [
            "Believe in yourself! 💪",
            "Keep pushing forward! 🚀",
            "Every day is a new opportunity! 🌟",
            "NeuraAI says: You can do it! 😎",
            "Success is built one step at a time! 🏆"
        ]
        print(f"Automation task: {random.choice(quotes)}")

    def random_math_challenge(self):
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        print(f"Automation task: Solve {a} + {b} = ?")

    def random_trivia_question(self):
        questions = [
            "Capital of France?",
            "Largest planet in the Solar System?",
            "Symbol for Gold?",
            "Fastest land animal?",
            "H2O represents what?"
        ]
        print(f"Automation task: Trivia - {random.choice(questions)}")

    def simple_alarm(self, message="Time's up!", seconds=3):
        print(f"Automation task: Alarm set for {seconds} seconds")
        time.sleep(seconds)
        print(f"ALARM: {message} ⏰")

    def mini_game_hint(self):
        hints = [
            "Remember the sequence carefully! 🔢",
            "Type as fast as you can! ⌨️",
            "Think before you move! 🧠",
            "Math is fun! ➕➖",
            "Focus on patterns! 🔍"
        ]
        print(f"Automation task: Mini-game hint - {random.choice(hints)}")

    def random_fact(self):
        facts = [
            "Did you know? The honeybee can recognize human faces! 🐝",
            "Fun fact: Octopuses have three hearts! 🐙",
            "Trivia: Bananas are berries, but strawberries aren't! 🍌",
            "Science: Water can boil and freeze at the same time! ❄️🔥",
            "Tech: The first computer virus was in 1986! 💻"
        ]
        print(f"Automation task: Fun Fact - {random.choice(facts)}")

    def celebrate_success(self):
        messages = [
            "🎉 Congratulations! Task completed!",
            "🥳 Well done! Keep it up!",
            "👏 Amazing work!",
            "💡 Great thinking!",
            "🤩 You nailed it!"
        ]
        print(f"Automation task: {random.choice(messages)}")