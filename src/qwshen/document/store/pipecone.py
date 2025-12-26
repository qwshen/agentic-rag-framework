from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

from qwshen.common.component import DocumentStore
from qwshen.common.argument import verify_all

class PipeconeVS(DocumentStore):
    _arg_api_key = "api_key"
    
    _arg_embedding: str = "embedding"
    _arg_index_name: str = "index_name"

    _arg_options: str = "options"
    _arg_options_spec: str = "spec"

    _args_required = [ _arg_api_key, _arg_embedding, _arg_index_name]

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=PipeconeVS._args_required):
            raise RuntimeError(f"Required args ({','.join(PipeconeVS._args_required)}) are not all defined.")
        
        n_kwargs = {}
        api_key = index_name = None
        for k_arg, w_arg in kwargs.items():
            if k_arg == PipeconeVS._arg_embedding:
                self._embedding_function = DocumentStore.create_embeddings(w_arg)
            elif k_arg == PipeconeVS._arg_api_key:
                api_key = w_arg
            elif k_arg == PipeconeVS._arg_index_name:
                index_name = w_arg
            elif k_arg == PipeconeVS._arg_options:
                n_kwargs = w_arg
                if PipeconeVS._arg_options_spec in w_arg:
                    n_kwargs[PipeconeVS._arg_options_spec] = ServerlessSpec(**w_arg["spec"])
        if self._embedding_function is None or api_key is None or index_name is None:
            raise ValueError("embedding, api_key and index_name are required.")

        pc = Pinecone(api_key=api_key)
        if not pc.has_index(index_name):
            n_kwargs["name"] = index_name
            n_kwargs["dimension"] = len(self._embedding_function.embed_query("test"))
            pc.create_index(**n_kwargs)
        self._interface = PineconeVectorStore(index=pc.Index(index_name), embedding=self._embedding_function)
        self.verify()
