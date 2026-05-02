import os
import time

from pydoc import locate
from typing import Iterator
from abc import abstractmethod, ABC
from queue import Queue
from typing import Callable
from types import NoneType
from copy import deepcopy

from langchain_core.documents.base import Document
from .utils import nvl

class Creator:
    def _create(self, type: str, kwargs: dict):
        return locate(type)(kwargs)
    
    @staticmethod
    def create(type: str, kwargs: dict):
        return locate(type)(**kwargs)

class DocumentHandler(Creator):
    _queue_docs_count = 0

    def __init__(self, queues: list[Queue]):
        if DocumentHandler._docs_batch_size() <= 0:
            raise ValueError("Batch size must be greater than 0")
        self._queues = queues

    def batch_documents(self, documents: list[Document]) -> Iterator[list[Document]]:
        docs_batch_size = DocumentHandler._docs_batch_size()
        batches = len(documents) // docs_batch_size
        for i in range(0, batches):
            yield documents[i*docs_batch_size: (i + 1)*docs_batch_size]
        if (len(documents) % docs_batch_size) > 0:
            yield documents[batches*docs_batch_size:]

    def _find_queue(self, id: int) -> Queue:
        queue_docs_limit = DocumentHandler._queue_docs_limit()
        if self._queues[id].qsize() < queue_docs_limit:
            return self._queues[id]

        for queue in [queue for idx, queue in enumerate(self._queues) if idx != id]:
            if queue.qsize() < queue_docs_limit:
                return queue
        return None
    
    def queue(self, documents: list[Document], source: str, done: bool = False):
        if documents is not None and len(documents) > 0:
            DocumentHandler._queue_docs_count += 1
            queue_id = DocumentHandler._queue_docs_count % len(self._queues)

            target_queue = self._find_queue(queue_id)
            while target_queue is None:
                time.sleep(0.5)
                target_queue = self._find_queue(queue_id)
            target_queue.put((documents, source, done))

        if done:
            for queue in self._queues:
                queue.put(([], source, True))

    @staticmethod
    def _docs_batch_size() -> int:
        return int(os.environ.get("DOCUMENTS_PROCESING_BATCH_SIZE", 9))
    @staticmethod
    def _queue_docs_limit() -> int:
        return int(os.environ.get("DOCUMENTS_QUEUE_MAX_SIZE", 4096))

class DocumentLoader(Creator, ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def load(self, handlerCallback: Callable[[list[Document], str], NoneType]):
        pass

    @abstractmethod
    def on_event(self, event: dict, handlerCallback: Callable[[list[Document], str], NoneType]):
        pass

class DocumentSplitter(Creator):
    def __init__(self, chunk_size_threshold: int = 64, chunk_size_strategy: str = "append"):
        super().__init__()
        self._chunk_size_threshold = chunk_size_threshold
        self._chunk_size_strategy = chunk_size_strategy

        self._splitter = None

    def split(self, documents: list[Document]):
        if self._splitter is None:
            raise RuntimeError("The splitter is not defined")
        return self.compact(self._splitter.split_documents(documents))

    @staticmethod
    def _append(doc1: Document, doc2: Document) -> Document:
        pc1 = doc1.page_content
        pc2 = doc2.page_content

        max_overlap = min(len(pc1), len(pc2))
        overlap_len = 0
        for j in range(max_overlap, 0, -1):
            if pc1[-j:] == pc2[:j]:
                overlap_len = j
                break

        doc1.page_content = doc1.page_content + " " +  pc2[overlap_len:]
        return doc1

    def compact(self, documents: list[Document]) -> list[Document]:
        if not documents or len(documents) == 0:
            return []
        elif self._chunk_size_strategy == "discard":
            chunk_size_threshold = self._chunk_size_threshold * 0.55
            return [document for document in documents if len(document.page_content) >= chunk_size_threshold]
        elif self._chunk_size_strategy == "append":
            compacted_documents = []
            chunk_size_threshold = self._chunk_size_threshold * 0.80
            docIdx = 0
            while docIdx < len(documents):
                while docIdx < len(documents) and len(documents[docIdx].page_content) >= chunk_size_threshold:
                    compacted_documents.append(deepcopy(documents[docIdx]))
                    docIdx = docIdx + 1

                if docIdx < len(documents):
                    document = deepcopy(documents[docIdx])
                    docIdx = docIdx + 1
                    while docIdx < len(documents):
                        document = DocumentSplitter._append(document, documents[docIdx])
                        docIdx = docIdx + 1
                        if len(document.page_content) >= chunk_size_threshold:
                            break
                    compacted_documents.append(document)
            return compacted_documents
        else:
            raise ValueError(f"Invalid chunk size strategy: {self._chunk_size_strategy}. Supported strategies are: discard, append")
    
class DocumentStorable(ABC):
    @abstractmethod
    def save(self):
        pass

class DocumentStore(Creator):
    def __init__(self):
        super().__init__()
        self._embedding_function = None
        self._interface = None

    def verify(self):
        if self._embedding_function is None or self._interface is None:
            raise RuntimeError(f"Either embedding_function or interface is not defined.")

    def get_vector_dimensions(self):
        return len(self._embedding_function.embed_query("Hello World!")) if self._embedding_function is not None else None

    def embed_query(self, query: str) -> list[float]:
        self.verify()
        return self._embedding_function.embed_query(query)

    def interface(self):
        return self._interface
    
    def embedding_function(self):
        return self._embedding_function
    
    def add_documents(self, documents: list[Document]) -> list[str]:
        self.verify()
        return self._interface.add_documents(documents)
    
    def close(self):
        pass

    @staticmethod
    def create_embeddings(embeddings: dict):
        embedding_type = embeddings.get("type", None)
        if embedding_type is None:
            raise RuntimeError("The embeddings-type is not defined.")
        embeddings_kwargs = embeddings.get("kwargs", {})
        return Creator.create(type = embedding_type, kwargs = embeddings_kwargs)

class DocumentIndexer(Creator, DocumentStorable):
    def __init__(self, store: DocumentStore):
        super().__init__()
        self._store = store

    @staticmethod
    def _remove_nul_bytes(document: Document) -> Document:
        if "\x00" in document.page_content:
            document.page_content = document.page_content.replace("\x00", "\ufffd")
        return document

    def add_document(self, document: Document)-> list[str]:
        return self.add_documents([ document ])

    def add_documents(self, documents: list[Document]) -> list[str]:      
        return self._store.add_documents([DocumentIndexer._remove_nul_bytes(document) for document in documents if len(document.page_content.strip()) > 0])

    def get_document(self, id: str) -> Document | None:
        documents = self.get_documents([id])
        return documents[0] if documents and len(documents) > 0 else None

    def get_documents(self, ids: list[str]) -> list[Document]:
        self._store.verify()
        return self._store.interface().get_by_ids(ids)
    
    def delete_document(self, id: str):
        self._store.verify()
        self._store.interface().delete([id])

    def delete_documents(self, ids: list[str]):
        self._store.verify()
        self._store.interface().delete(ids)

    def save(self):
        self._store.verify()
        if isinstance(self._store, DocumentStorable):
            self._store.save()

class DocumentSearcher(Creator):
    def __init__(self, store: DocumentStore, \
            type: str, fetch_k: int = 20, score_threshold: float = 0, lambda_mult: float = 0.5, k: int = 4, kwargs: dict = {}):
        super().__init__()
        self._store = store

        # type: the type of the searcher:
        # similarity - regular similarity search
        # similarity_score_threshold - return documents whose similarity score exceeds a given threshold.
        # mmr - max marginal relevance. A re-ranking algorithm used after an initial document retrieval step. It selects a set of results that are Highly relevant to the query, and Not too similar to each other.
        self._type = type
        # fetch_k: number of documents to fetch from vector store before filtering. Defaults to 20.
        self._fetch_k = fetch_k
        # score_threshold: a floating point value between 0 to 1 to filter the resulting set of retrieved docs by its relevance score. Defaults to 0.
        self._score_threshold = score_threshold
        # lambda_mult: number between 0 and 1 that determines the degree of diversity among the results with 0 corresponding to maximum diversity and 1 to minimum diversity. Defaults to 0.5.
        self._lambda_mult = lambda_mult
        # k: number of documents to return. Defaults to 4.
        self._k = k
        # kwargs: additional keyword arguments for the searcher
        self._kwargs = kwargs

    def similarity_search(self, query: str, k: int = None, kwargs: dict = None) -> list[Document]:
        self._store._self_verify()
        return self._store.similarity_search(query, nvl(k, self._k), **nvl(kwargs, self._kwargs))

    def similarity_search_by_vector(self, query: str, k: int = None, kwargs: dict = None) -> list[Document]:
        self._store._self_verify()
        return self._store.similarity_search_by_vector(self._embedding_function.embed_query(query), nvl(k, self._k), **nvl(kwargs, self._kwargs))

    def mmr_search(self, query: str, fetch_k: int = None, lambda_mult: float = None, k: int = None, kwargs: dict = None) -> list[Document]:
        self._store._self_verify()
        return self._store.max_marginal_relevance_search(query, nvl(k, self._k), nvl(fetch_k, self._fetch_k), nvl(lambda_mult, self._lambda_mult), **nvl(kwargs, self._kwargs))

    def mmr_search_by_vector(self, query: str, fetch_k: int = None, lambda_mult: float = None, k: int = None, kwargs: dict = None):
        self._store._self_verify()
        embedding_vector = self._embedding_function.embed_query(query)
        return self._store.max_marginal_relevance_search_by_vector(embedding_vector, nvl(k, self._k), nvl(fetch_k, self._fetch_k), nvl(lambda_mult, self._lambda_mult), **nvl(kwargs, self._kwargs))

    def search(self, search_type: str, kwargs: dict) -> list[Document]:
        self._store._self_verify()
        if search_type not in ["similarity", "similarity_score_threshold", "mmr"]:
            raise ValueError(f"Invalid search type: {search_type}. Supported types are: similarity, similarity_score_threshold, mmr")
        kwargs["fetch_k"] = nvl(kwargs.get("fetch_k"), self._fetch_k)
        kwargs["score_threshold"] = nvl(kwargs.get("score_threshold"), self._score_threshold)
        kwargs["lambda_mult"] = nvl(kwargs.get("lambda_mult"), self._lambda_mult)
        kwargs["k"] = nvl(kwargs.get("k"), self._k)
        return self._store.search(search_type, **kwargs)

    def similarity_search_with_relevance_scores(self, query: str, k: int = None, kwargs: dict = None) -> list[(Document, float)]:
        self._store._self_verify()
        return self._store.asimilarity_search_with_relevance_scores(query, nvl(k, self._k), **nvl(kwargs, self._kwargs))

    def similarity_search_with_distance(self, query: str, k: int = None, filter: dict = None, kwargs: dict = None) -> list[(Document, float)]:
        self._self_verify()
        return self._store.asimilarity_search_with_score(query, nvl(k, self._k), filter, **nvl(kwargs, self._kwargs))

class DocumentRetriever(DocumentSearcher):
    def __init__(self, interface: DocumentStore, \
            type: str, fetch_k: int = 20, score_threshold: float = 0, lambda_mult: float = 0.5, k: int = 4, kwargs: dict = {}):
        super().__init__(interface, type, fetch_k, score_threshold, lambda_mult, k, kwargs)

    def getRetriever(self):
        self._store._self_verify()
        return self._store.as_retriever(search_type=self._type, search_kwargs={"fetch_k": self._fetch_k, "score_threshold": self._score_threshold, "lambda_mult": self._lambda_mult, "fetch_k": self._fetch_k, "kwargs": self._kwargs })

class Runner(Creator):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def run(self):
        pass
