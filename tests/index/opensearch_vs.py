
# Please set up your OpenSearch before running this test.
# You can use the following Docker commands to set it up:
#
# docker pull opensearchproject/opensearch:latest
# docker run -d -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" -e "plugins.security.disabled=true" -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=PwD4aDm@LoCAl" opensearchproject/opensearch:latest
#

from pathlib import Path
from qwshen.launcher import test_index
from unittest.mock import patch

tests_dir = Path(__file__).resolve().parent.parent
args = [
  "", 
  "--def", str(tests_dir / f"defs/index/opensearch_vs.json"), 
  "--env", str(tests_dir / "application.env")
]
with patch("sys.argv", args):
  test_index()    