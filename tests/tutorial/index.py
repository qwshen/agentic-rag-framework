from pathlib import Path
from qwshen.launcher import test_index
from unittest.mock import patch

app_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(app_dir / f"tutorial/index.json"), 
  "--env", str(app_dir / f"tutorial/app.env")
]
with patch("sys.argv", args):
  test_index()