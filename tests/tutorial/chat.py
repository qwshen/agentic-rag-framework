import os
import sys
from pathlib import Path
from qwshen.launcher import Launcher
from unittest.mock import patch

##########################################################################################################
# Note: 
#  In order to run this test, please run by_schedule.py first to index the documents used in this test.
##########################################################################################################

app_dir = Path(__file__).resolve().parent.parent
os.environ["PROMPTS_DIRECTORY"] = str(app_dir / "chat/prompts")
args = [
  "", 
  "--def", str(app_dir / f"tutorial/chat.json"), 
  # "--def", str(app_dir / f"tutorial/chat_with_history.json"), 
  # "--def", str(app_dir / f"tutorial/agentic_chat.json"), 
  "--env", str(app_dir / f"tutorial/app.env")
]
session_id = "it_learning_chat_session_001"
with patch("sys.argv", args):
    _, services = Launcher.start()

    print("Welcome to the IT Learning Chat! You can ask questions about IT learning resources, and I'll do my best to help you find the information you need. Type 'exit' to end the chat.")
    while True:
        question = input("You: ").strip()
        if len(question) == 0:
            print("Please type a valid question ...")
            continue  
        if question.lower() == "exit":
            print("Exiting ...")
            break
        
        for service, _ in services:
            print(f"Answer [by {service.get_name()}]: ", end="", flush=True)
            for message in service.process(question, kwargs={"session_id": session_id}):
                print(message.content if message is not None else "\n", end="", flush=True)
