from qwshen.common.component import DocumentSplitter, Creator
from qwshen.common.logging import RagLogger

class TextSplitter(DocumentSplitter):
    def __init__(self, kwargs: dict):
        super().__init__(kwargs.get("chunk_size_threshold", 64), kwargs.get("chunk_size_strategy", "append"))

        worker = kwargs.get("worker", None)
        if worker is None:
            RagLogger.logger().error("Worker is required for TextSplitter")
            raise RuntimeError("Worker is required for TextSplitter")
        self._splitter = Creator.create(**worker)