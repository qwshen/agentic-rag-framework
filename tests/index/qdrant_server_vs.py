
# Please set up your Qdrant instance before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull qdrant/qdrant:latest
# docker run -d --name qdrant-server -p 6333:6333 -p 6334:6334 -e QDRANT__SERVICE__API_KEY="test-api-key" -v "/opt/agentic-rag-1.0.0/db/qdrant/server:/qdrant/storage" qdrant/qdrant:latest
#

from pathlib import Path
from qwshen.launcher import test_index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"defs/index/qdrant_server_vs.json"), 
  "--env", str(tests_dir / "application.env")
]
with patch("sys.argv", args):
  test_index()    