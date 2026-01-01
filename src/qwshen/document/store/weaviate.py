from urllib import response
from annotated_types import doc
import weaviate
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_core.documents.base import Document

from qwshen.common.component import DocumentStore
from qwshen.common.argument import verify_all

class WeaviateVS(DocumentStore):
    _arg_embedding: str = "embeddings"

    _arg_client: str = "client"
    _arg_index_name: str = "index_name"
    _arg_text_key: str = "text"

    _args_required = [_arg_embedding, _arg_client]

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=WeaviateVS._args_required):
            raise RuntimeError(f"Required args ({','.join(WeaviateVS._args_required)}) are not all defined.")
        
        embedding = client = index_name = None
        for k_arg, w_arg in kwargs.items():
            if k_arg == WeaviateVS._arg_embedding:
                embedding = DocumentStore.create_embeddings(w_arg)
            elif k_arg == WeaviateVS._arg_client:
                client = self._create_client(w_arg)
            elif k_arg == WeaviateVS._arg_index_name:
                index_name = w_arg
        if embedding is None or client is None:
            raise RuntimeError("Either embedding, or client is not defined.")

        self._client = client
        self._embedding_function = embedding

        self._interface = WeaviateVectorStore(client=client, index_name=index_name, embedding=embedding, text_key=WeaviateVS._arg_text_key)
        self._collection = client.collections.get("default")
        self.verify()
        self._client.connect()

    def _create_client(self, config: dict):
        mode = config.get("mode", "embedded")
        options = config.get("options", {})
        if mode == "embedded":
            return weaviate.connect_to_embedded(**options)
        elif mode == "local":
            return weaviate.connect_to_local(**options)
        elif mode == "custom":
            return weaviate.connect_to_custom(**options)
        elif mode == "cloud":
            return weaviate.connect_to_weaviate_cloud(**options)
        else:
            raise RuntimeError(f"Unsupported Weaviate client mode: {mode}")

    def verify(self):
        if self._embedding_function is None or self._interface is None or self._collection is None:
            raise RuntimeError(f"Either embedding_function or interface or collection is not defined.")

    def add_documents(self, documents: list[Document]) -> list[str]:
        self.verify()
        docs_to_insert = [{ WeaviateVS._arg_text_key: doc.page_content, **doc.metadata } for doc in documents]
        response = self._collection.data.insert_many(docs_to_insert)
        if response.has_errors:
            raise RuntimeError(f"Failed to insert documents - {response.errors}.")
        return response.uuids.values()

    def close(self):
        self._client.close()

    def __del__(self):
        self.close()
