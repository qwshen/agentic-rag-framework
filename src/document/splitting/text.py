from common.component import DocumentSplitter, DocumentHandler, Creator
from common.logging import RagLogger

class TextSplitter(DocumentSplitter):
    def __init__(self, kwargs: dict):
        super().__init__()

        worker = kwargs.get("worker", None)
        if worker is None:
            RagLogger.logger().error("Worker is required for TextSplitter")
            raise RuntimeError("Worker is required for TextSplitter")
        self._splitter = Creator.create(**worker)