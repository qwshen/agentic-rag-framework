from langchain_community.vectorstores import OpenSearchVectorSearch

from qwshen.common.component import DocumentStore
from qwshen.common.argument import verify_all

class OpenSearchVS(DocumentStore):
    _arg_opensearch_url: str = "opensearch_url"
    _arg_index_name: str = "index_name"

    _arg_embedding_function: str = "embedding_function"

    _args_required = [_arg_embedding_function, _arg_opensearch_url, _arg_index_name]

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=OpenSearchVS._args_required):
            raise RuntimeError(f"Required args ({','.join(OpenSearchVS._args_required)}) are not all defined.")

        n_kwargs = {}
        for k_arg, w_arg in kwargs.items():
            if k_arg == OpenSearchVS._arg_embedding_function:
                n_kwargs[OpenSearchVS._arg_embedding_function] = DocumentStore.create_embeddings(w_arg)
            else:
                n_kwargs[k_arg] = w_arg

        self._embedding_function = n_kwargs.get(OpenSearchVS._arg_embedding_function, None)
        self._interface = OpenSearchVectorSearch(**n_kwargs)
        self.verify()
