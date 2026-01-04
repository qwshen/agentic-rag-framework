
from pathlib import Path
from qwshen.launcher import test_index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"defs/index/by_schedules.json"), 
  "--env", str(tests_dir / "application.env")
]
with patch("sys.argv", args):
  test_index()    