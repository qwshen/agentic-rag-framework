
# Please set up your PostgreSQL with pgvector extension before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull pgvector/pgvector:pg16
# docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
#
# After running the above command, please update the connection information in app.env file according to your setup.
#

from pathlib import Path
from unittest.mock import patch
import time
from functools import reduce

from qwshen.launcher import Launcher

def test_index():
    indexers, _ = Launcher.start()
    if reduce(lambda x, y: x or y, [indexer.index_scheduled() for indexer in indexers], False):
        try:
            print("Indexing scheduled. Press Ctrl+C to exit.")
            while True:
                time.sleep(30)
        except (KeyboardInterrupt, SystemExit):
            pass

app_dir = Path(__file__).resolve().parent
args = [
  "", 
  "--def", str(app_dir / f"index.json"), 
  "--env", str(app_dir / f"app.env")
]
with patch("sys.argv", args):
  test_index()