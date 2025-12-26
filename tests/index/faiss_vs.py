
from pathlib import Path
from qwshen.launcher import main
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"resources/index/faiss_vs.json"), 
  "--env", str(tests_dir / "resources/application.env")
]
with patch("sys.argv", args):
  main()    