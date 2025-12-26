from urllib.parse import urlparse

from langchain_milvus import Milvus
from pymilvus import MilvusException, connections, db, utility

from qwshen.common.component import DocumentStore
from qwshen.common.argument import verify_all

class MilvusVS(DocumentStore):
    _arg_connection_args = "connection_args"
    _arg_embedding_function: str = "embedding_function"
    
    _args_required = [ _arg_connection_args, _arg_embedding_function]

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=MilvusVS._args_required):
            raise RuntimeError(f"Required args ({','.join(MilvusVS._args_required)}) are not all defined.")
        
        n_kwargs = {}
        uri = db_name = None
        for k_arg, w_arg in kwargs.items():
            if k_arg == MilvusVS._arg_embedding_function:
                n_kwargs[MilvusVS._arg_embedding_function] = DocumentStore.create_embeddings(w_arg)
            else:
                if k_arg == MilvusVS._arg_connection_args:
                    uri = w_arg.get("uri", None)
                    db_name = w_arg.get("db_name", None)
                n_kwargs[k_arg] = w_arg

        if uri is None:
            raise ValueError("Connection URI is required.")
        parsed_uri = urlparse(uri)
        if parsed_uri.scheme in ["http", "https"]:
            if db_name is not None:
                self._verify_db(parsed_uri.hostname, parsed_uri.port, db_name)

        self._embedding_function = n_kwargs.get(MilvusVS._arg_embedding_function, None)
        self._interface = Milvus(**n_kwargs)
        self.verify()

    def _verify_db(self, host: str, port: str, db_name: str):
        connections.connect("default", host=host, port=port)
        try:
            existing_databases = db.list_database()
            if db_name not in existing_databases:
                db.create_database(db_name)
        except MilvusException as me:
            raise RuntimeError(f"Failed to verify or create database '{db_name}': {me}")
        finally:
            connections.disconnect("default")
