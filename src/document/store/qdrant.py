from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from common.component import DocumentIndexer, DocumentStore
from common.argument import verify_all, verify_any

class QdrantVS(DocumentStore):
    _arg_embedding: str = "embedding"

    _arg_db_server: str = "db_server"
    _arg_db_path: str = "db_path"

    _arg_collection: str = "collection"

    _args_required = [_arg_embedding, _arg_collection]
    _args_any = [_arg_db_server, _arg_db_path]

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=QdrantVS._args_required):
            raise RuntimeError(f"Required args ({','.join(QdrantVS._args_required)}) are not all defined.")
        elif not verify_any(kwargs, kany=QdrantVS._args_any):
            raise RuntimeError(f"Only one of {QdrantVS._args_any} can be configured.")
        
        embedding = client = collection_name = vector_params = None
        for k_arg, w_arg in kwargs.items():
            if k_arg == QdrantVS._arg_embedding:
                embedding = DocumentStore.create_embeddings(w_arg)
            elif k_arg == QdrantVS._arg_collection:
                collection_name = w_arg.get("name")
                vector_params = dict([(k, Distance[v] if k == "distance" else v) for k, v in w_arg.get("vector_params", {}).items()])
            elif k_arg == QdrantVS._arg_db_server:
                client = QdrantClient(**w_arg)
            elif k_arg == QdrantVS._arg_db_path:
                client = QdrantClient(path=w_arg)
        if embedding is None or client is None or collection_name is None:
            raise RuntimeError("Either embedding, client or collection is not defined.")
        elif vector_params is None:
            vector_params = { "distance": "COSINE" }

        vector_params["size"] = len(embedding.embed_query("test"))
        collection = {"collection_name": collection_name, "vectors_config": VectorParams(**vector_params)}

        if not client.collection_exists(collection.get("collection_name")):
            client.create_collection(**collection)

        self._embedding_function = embedding
        self._interface = QdrantVectorStore(client=client, collection_name=collection.get("collection_name"), embedding=embedding)
        self.verify()
