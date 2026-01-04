import os
from pathlib import Path
from qwshen.launcher import test_answer
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
os.environ["PROMPTS_DIRECTORY"] = str(tests_dir / "chat/prompts")
args = [
  "", 
  "--def", str(tests_dir / f"defs/chat/chat_with_history.json"), 
  "--env", str(tests_dir / "application.env")
]
session_id = "test_chat_session_001"
questions = ["What is Kafka?", "Explain event streaming.", "List a few use cases of Kafka."]
with patch("sys.argv", args):
    test_answer(questions, session_id=session_id)    