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
