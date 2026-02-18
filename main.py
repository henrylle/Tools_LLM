# main.py
from agent import Agent
from tools import execute
import json
import sys
import threading
import time

agent = Agent()

def spinner(stop_event):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{frames[idx]} Thinking...")
        sys.stdout.flush()
        idx = (idx + 1) % len(frames)
        time.sleep(0.07)
    sys.stdout.write("\r" + " " * 20 + "\r")
    sys.stdout.flush()

print("Digite um comando em linguagem natural\n")

while True:
    user_input = input("> ")

    if user_input.lower() in ["exit", "quit"]:
        break

    try:
        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
        spinner_thread.start()
        
        command = agent.think(user_input)
        
        stop_event.set()
        spinner_thread.join()

        result = execute(command)
        print(result)

    except Exception as e:
        if 'stop_event' in locals():
            stop_event.set()
            spinner_thread.join()
        print("❌ Erro:", e)
