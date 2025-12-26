from qwshen.common.component import DocumentStore
from qwshen.common.argument import verify_all

from langchain_postgres import PGVector

class PgVectorVS(DocumentStore):
    _arg_collection_name = "collection_name"
    _arg_connection: str = "connection"

    _arg_embeddings: str = "embeddings"
    _arg_use_jsonb: str = "use_jsonb"
    
    _args_required = [ _arg_collection_name, _arg_connection, _arg_embeddings]

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=PgVectorVS._args_required):
            raise RuntimeError(f"Required args ({','.join(PgVectorVS._args_required)}) are not all defined.")
        
        n_kwargs = {}
        for k_arg, w_arg in kwargs.items():
            if k_arg == PgVectorVS._arg_embeddings:
                n_kwargs[PgVectorVS._arg_embeddings] = DocumentStore.create_embeddings(w_arg)
            else:
                n_kwargs[k_arg] = w_arg
        if PgVectorVS._arg_use_jsonb not in n_kwargs:
            n_kwargs[PgVectorVS._arg_use_jsonb] = True

        self._embedding_function = n_kwargs.get(PgVectorVS._arg_embeddings, None)
        self._interface = PGVector(**n_kwargs)
        self.verify()
