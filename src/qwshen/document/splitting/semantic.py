from langchain_core.documents.base import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from qwshen.common.component import DocumentSplitter, Creator
from qwshen.common.logging import RagLogger

class SemanticSplitter(DocumentSplitter):
    def __init__(self, kwargs: dict):
        super().__init__()

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

        self._pre_spliiter = None
        initial_chunk_size = kwargs.get("initial_chunk_size", None)
        if initial_chunk_size is not None:
            self._pre_spliiter = RecursiveCharacterTextSplitter(chunk_size=initial_chunk_size, chunk_overlap=0)

    def split(self, documents: list[Document]):
        if self._splitter is None:
            raise RuntimeError("The splitter is not defined")

        if self._pre_spliiter is not None:
            documents = self._pre_spliiter.split_documents(documents)
        return self._splitter.split_documents(documents)
