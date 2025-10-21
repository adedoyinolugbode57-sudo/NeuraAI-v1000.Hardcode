"""
mini_games.py — 100+ mini-games for NeuraAI_v200
Author: CHATGPT + Joshua•Dav
"""

import random

GAMES_LIST = [
    # 1-10
    "Guess a number between 1-10",
    "Rock, Paper, Scissors",
    "Simple Math Quiz: 5+7=?",
    "Word Unscramble: 'RACT'",
    "Quick Typing Test: Type 'NeuraAI'",
    "Find the hidden letter in 'ALPGH'",
    "Memory Test: Remember 12345",
    "Reverse the word 'Python'",
    "Guess the color: Red, Blue, Green?",
    "Trivia: Capital of France?",

    # 11-20
    "Math Challenge: 12*3=?",
    "Spell the word 'Intelligence'",
    "Unscramble: 'OGARHMLI'",
    "Quick: Type 'AI Rocks!'",
    "Riddle: What has keys but can't open locks?",
    "Guess a number between 20-30",
    "Trivia: 1+1=?",
    "Find the odd one out: Cat, Dog, Car",
    "Memory: Repeat 2468",
    "Math: 45/5=?",

    # 21-30
    "Unscramble: 'NVTERA'",
    "Trivia: Largest planet in solar system",
    "Quick Typing: 'NeuraAI is amazing!'",
    "Riddle: I speak without a mouth. What am I?",
    "Math Challenge: 9*9=?",
    "Guess the number between 50-60",
    "Memory: Remember 'ABCDEF'",
    "Word Puzzle: Synonym of 'Happy'",
    "Trivia: Currency of Japan?",
    "Unscramble: 'ACETM'",

    # 31-40
    "Quick Math: 100-37=?",
    "Riddle: What runs but never walks?",
    "Memory: Remember 314159",
    "Trivia: Fastest land animal?",
    "Word Scramble: 'GNIRHTE'",
    "Math Challenge: 8*7=?",
    "Guess a number between 70-80",
    "Trivia: Author of '1984'?",
    "Quick Typing: 'ChatGPT is cool!'",
    "Unscramble: 'LBOAC'",

    # 41-50
    "Memory Test: Repeat 97531",
    "Math: 56+44=?",
    "Trivia: H2O is?",
    "Riddle: What has hands but can't clap?",
    "Word Unscramble: 'YLLAUNF'",
    "Guess the number 1-100",
    "Trivia: Currency of USA",
    "Quick Typing: 'AI forever!'",
    "Memory: Remember 'XYZ123'",
    "Math Challenge: 15*6=?",

    # 51-60
    "Riddle: What can travel around the world but stays in corner?",
    "Trivia: Deepest ocean?",
    "Unscramble: 'RAHCET'",
    "Quick: Type 'NeuraAI rules!'",
    "Memory: Remember 8642",
    "Math: 120/12=?",
    "Guess the number between 30-40",
    "Trivia: Tallest mountain?",
    "Word Puzzle: Opposite of 'Cold'",
    "Riddle: What gets wetter as it dries?",

    # 61-70
    "Math Challenge: 33+67=?",
    "Unscramble: 'TACOP'",
    "Memory: Repeat 'LMNOP'",
    "Trivia: Planet closest to Sun",
    "Quick Typing: 'I love AI!'",
    "Riddle: Forward I am heavy, backward I am not. What am I?",
    "Guess the number between 10-20",
    "Math: 14*12=?",
    "Trivia: Largest ocean?",
    "Unscramble: 'LEPPHA'",

    # 71-80
    "Memory Test: Remember 111213",
    "Quick Typing: 'NeuraAI v200!'",
    "Trivia: Who invented Light Bulb?",
    "Math Challenge: 99-45=?",
    "Riddle: What has a neck but no head?",
    "Word Scramble: 'RICTAE'",
    "Guess a number between 80-90",
    "Memory: Remember 'QWERTY'",
    "Trivia: First president of USA?",
    "Quick Typing: 'AI is future!'",

    # 81-90
    "Math: 72/8=?",
    "Riddle: I’m tall when I’m young, short when I’m old. What am I?",
    "Unscramble: 'RAEC'",
    "Memory Test: Repeat 121314",
    "Trivia: Largest desert?",
    "Quick Typing: 'NeuraAI rocks!'",
    "Math Challenge: 11*11=?",
    "Guess the number 5-15",
    "Riddle: What goes up but never comes down?",
    "Word Puzzle: Synonym of 'Fast'",

    # 91-100+
    "Trivia: Element symbol for Gold?",
    "Memory: Remember 202324",
    "Quick Typing: 'AI forever in my heart!'",
    "Math: 50*2=?",
    "Unscramble: 'LITHE'",
    "Riddle: What has a face and two hands but no arms or legs?",
    "Trivia: Capital of Italy?",
    "Guess the number 60-70",
    "Word Scramble: 'PLANE'",
    "Quick Math: 123+77=?"
]

def random_game():
    """Return a random mini-game"""
    return random.choice(GAMES_LIST)