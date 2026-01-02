
# Please set up your PostgreSQL with pgvector extension before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull pgvector/pgvector:pg16
# docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
#

from pathlib import Path
from qwshen.launcher import index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"resources/index/pgvector_vs.json"), 
  "--env", str(tests_dir / "resources/application.env")
]
with patch("sys.argv", args):
  index()    