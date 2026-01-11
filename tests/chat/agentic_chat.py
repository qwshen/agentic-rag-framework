import os
from pathlib import Path
from qwshen.launcher import test_answer
from unittest.mock import patch

##########################################################################################################
# Note: 
#  In order to run this test, please run by_schedule.py first to index the documents used in this test.
##########################################################################################################

tests_dir = Path(__file__).resolve().parent.parent
os.environ["PROMPTS_DIRECTORY"] = str(tests_dir / "chat/prompts")
args = [
  "", 
  "--def", str(tests_dir / f"defs/chat/agentic_chat.json"), 
  "--env", str(tests_dir / "application.env")
]
session_id = "test_chat_session_001"

# positive test cases
questions = ["What is Kafka?", "Explain event streaming.", "List a few use cases of Kafka."]
with patch("sys.argv", args):
    test_answer(questions, session_id=session_id)

# negative test cases
questions = ["What is the capital of Mars?", "Explain the color of sound.", "List a few use cases of perpetual motion machines."]
with patch("sys.argv", args):
    test_answer(questions, session_id=session_id)