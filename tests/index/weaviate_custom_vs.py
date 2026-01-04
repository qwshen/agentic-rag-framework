# Please set up your Weaviate instance before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull cr.weaviate.io/semitechnologies/weaviate:latest
# docker run -d --name weaviate-server -p 8080:8080 -p 50051:50051 -v "/opt/agentic-rag-1.0.0/db/weaviate:/var/lib/weaviate" -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true -e AUTHENTICATION_APIKEY_ENABLED=true -e AUTHENTICATION_APIKEY_ALLOWED_KEYS="test-secret-key" -e AUTHENTICATION_APIKEY_USERS=admin-user -e PERSISTENCE_DATA_PATH=/var/lib/weaviate -e DEFAULT_VECTORIZER_MODULE=none -e CLUSTER_HOSTNAME=node1 cr.weaviate.io/semitechnologies/weaviate:latest
#


from pathlib import Path
from qwshen.launcher import test_index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"defs/index/weaviate_custom_vs.json"), 
  "--env", str(tests_dir / "application.env")
]
with patch("sys.argv", args):
  test_index()    