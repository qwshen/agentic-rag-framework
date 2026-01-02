
from pathlib import Path
from qwshen.launcher import index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"resources/index/weaviate_embedded_vs.json"), 
  "--env", str(tests_dir / "resources/application.env")
]
with patch("sys.argv", args):
  index()    