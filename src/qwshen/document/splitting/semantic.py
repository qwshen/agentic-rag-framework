from langchain_core.documents.base import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from qwshen.common.component import DocumentSplitter, Creator
from qwshen.common.logging import RagLogger

class SemanticSplitter(DocumentSplitter):
    def __init__(self, kwargs: dict):
        super().__init__(kwargs.get("chunk_size_threshold", 64), kwargs.get("chunk_size_strategy", "append"))

        worker = kwargs.get("worker", None)
        if worker is None:
            RagLogger.logger().error("Worker is required for SemanticSplitter.")
            raise RuntimeError("Worker is required for SemanticSplitter.")
        worker_type = worker.get("type", None)
        if worker_type is None:
            RagLogger.logger().error("Worker type is required for SemanticSplitter.")
            raise RuntimeError("Worker type is required for SemanticSplitter.")
        worker_kwargs = {**worker.get("kwargs", {})}
        if "embeddings" in worker_kwargs:
            worker_kwargs["embeddings"] = Creator.create(**worker_kwargs.get("embeddings"))
        self._splitter = Creator.create(type=worker_type, kwargs=worker_kwargs)
