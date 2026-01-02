
# Please set up your PostgreSQL with pgvector extension before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull milvusdb/milvus:latest
# docker run -d --name milvus-server -p 19530:19530 -p 9091:9091 -e ETCD_USE_EMBED=true -e ETCD_DATA_DIR=/var/lib/milvus/etcd -e DEPLOY_MODE=STANDALONE -e COMMON_SECURITY_AUTHORIZATIONENABLED=true -v /opt/agentic-rag-1.0.0/db/milvus/server:/var/lib/milvus -e COMMON_STORAGETYPE=local milvusdb/milvus:latest milvus run standalone
#

from pathlib import Path
from qwshen.launcher import index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"resources/index/milvus_server_vs.json"), 
  "--env", str(tests_dir / "resources/application.env")
]
with patch("sys.argv", args):
  index()    