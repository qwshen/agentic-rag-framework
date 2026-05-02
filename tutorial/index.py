
# Please set up your PostgreSQL with pgvector extension before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull pgvector/pgvector:pg16
# docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
#
# After running the above command, please update the connection information in app.env file according to your setup.
#

from pathlib import Path
from qwshen.launcher import test_index
from unittest.mock import patch

app_dir = Path(__file__).resolve().parent
args = [
  "", 
  "--def", str(app_dir / f"index.json"), 
  "--env", str(app_dir / f"app.env")
]
with patch("sys.argv", args):
  test_index()