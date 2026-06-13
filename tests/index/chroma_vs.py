
from pathlib import Path
from unittest.mock import patch

from base import test_index

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"defs/index/chroma_vs.json"), 
  "--env", str(tests_dir / "application.env")
]
with patch("sys.argv", args):
  test_index()    