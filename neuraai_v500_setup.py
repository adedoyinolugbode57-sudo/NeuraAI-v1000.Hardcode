"""
NeuraAI v500 Full Setup & Launcher
Author: CHATGPT + Joshua•Dav
"""

import os
import subprocess
import sys
import json
import time

# ----------------------------
# Helper: run shell commands safely
# ----------------------------
def run_cmd(cmd_list):
    try:
        subprocess.check_call(cmd_list)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Command failed: {e}")

# ----------------------------
# Step 1: Upgrade pip
# ----------------------------
print("🔹 Upgrading pip...")
run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

# ----------------------------
# Step 2: Install dependencies
# ----------------------------
print("🔹 Installing required Python packages...")
if os.path.exists("requirements.txt"):
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
else:
    print("⚠️ requirements.txt not found! Make sure it is in the folder.")

# ----------------------------
# Step 3: Ensure JSON backups
# ----------------------------
for json_file in ["chat_logs.json", "memory_store.json"]:
    if not os.path.exists(json_file):
        with open(json_file, "w") as f:
            json.dump({}, f)
        print(f"✅ Created {json_file}")

# ----------------------------
# Step 4: Create optional folders
# ----------------------------
for folder in ["backend", "frontend"]:
    if not os.path.exists(folder):
        os.mkdir(folder)
        print(f"✅ Created folder {folder}")

# ----------------------------
# Step 5: Launch main.py
# ----------------------------
main_file = "main.py"
if not os.path.exists(main_file):
    print(f"⚠️ {main_file} not found! Make sure it's in the folder.")
else:
    print("✅ Setup complete! Launching NeuraAI v500...")

    # Optional prompt for premium & voice mode
    use_voice = input("Enable voice engine by default? (y/n): ").strip().lower() == "y"
    is_premium = input("Run in premium mode? (y/n): ").strip().lower() == "y"

    # Build launch command
    launch_cmd = f'{sys.executable} {main_file}'

    print("🔹 NeuraAI v500 is starting...")
    # Pass environment variables to main.py for premium & voice
    os.environ["NEURAAI_PREMIUM"] = "true" if is_premium else "false"
    os.environ["NEURAAI_VOICE"] = "true" if use_voice else "false"

    time.sleep(1)
    os.system(launch_cmd)