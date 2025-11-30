from langchain_chroma import Chroma

from common.component import DocumentStore
from common.argument import verify_all

class ChromaVS(DocumentStore):
    _arg_store_file: str = "store_file"
    _arg_embeddings: str = "embeddings"

    _arg_collection_name = "collection_name"
    _arg_persist_directory = "persist_directory"
    _arg_embedding_function = "embedding_function"

    _args_required = [_arg_store_file, _arg_embeddings]

    def __init__(self, kwargs: dict):
        super().__init__()
        
        if not verify_all(kwargs, kall=ChromaVS._args_required):
            raise RuntimeError(f"Required args ({','.join(ChromaVS._args_required)}) are not all defined.")
        
        n_kwargs = {}
        for k_arg, w_arg in kwargs.items():
            if k_arg == ChromaVS._arg_store_file:
                persist_directory, collection_name = w_arg.rsplit("/", 1)
                n_kwargs[ChromaVS._arg_collection_name] = collection_name
                n_kwargs[ChromaVS._arg_persist_directory] = persist_directory
            elif k_arg == ChromaVS._arg_embeddings:
                n_kwargs[ChromaVS._arg_embedding_function] = DocumentStore.create_embeddings(w_arg)
            else:
                n_kwargs[k_arg] = w_arg

        self._embedding_function = n_kwargs.get(ChromaVS._arg_embedding_function, None)
        self._interface = Chroma(**n_kwargs)
        self.verify()
