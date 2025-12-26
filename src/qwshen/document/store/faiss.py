import os
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss

from qwshen.common.component import DocumentStorable, DocumentStore
from qwshen.common.argument import verify_all

class FaissVS(DocumentStore, DocumentStorable):
    _p_file_extension = "faiss"

    _arg_store_file: str = "store_file"
    _arg_embeddings: str = "embeddings"

    _arg_folder_path: str = "folder_path"
    _arg_index_name: str = "index_name"
    _arg_index = "index"
    _arg_docstore: str = "docstore"
    _arg_index_to_docstore_id = "index_to_docstore_id"
    _arg_allow_dangerous_deserialization: str = "allow_dangerous_deserialization"

    _args_required = [_arg_store_file, _arg_embeddings]
    _arg_embedding_function = "embedding_function"

    def __init__(self, kwargs: dict):
        super().__init__()

        if not verify_all(kwargs, kall=FaissVS._args_required):
            raise RuntimeError(f"Required args ({','.join(FaissVS._args_required)}) are not all defined.")

        n_kwargs = {}
        self._embedding_function = None
        for k_arg, w_arg in kwargs.items():
            if k_arg == FaissVS._arg_store_file:
                self._store_path, self._store_file = w_arg.rsplit("/", 1)
            elif k_arg == FaissVS._arg_embeddings:
                self._embedding_function = DocumentStore.create_embeddings(w_arg)
            else:
                n_kwargs[k_arg] = w_arg
        if self._embedding_function is None:
            raise RuntimeError("The embedding function is not defined for Faiss")
        
        store_file = f"{self._store_path}/{self._store_file}.{FaissVS._p_file_extension}"
        if os.path.exists(store_file):
            n_kwargs[FaissVS._arg_embeddings] = self._embedding_function
            n_kwargs[FaissVS._arg_folder_path] = self._store_path
            n_kwargs[FaissVS._arg_index_name] = self._store_file
            n_kwargs[FaissVS._arg_allow_dangerous_deserialization] = True
            self._interface = FAISS.load_local(**n_kwargs)
        else:
            n_kwargs[FaissVS._arg_docstore] = InMemoryDocstore()                
            n_kwargs[FaissVS._arg_embedding_function] = self._embedding_function
            if FaissVS._arg_index not in n_kwargs:
                n_kwargs[FaissVS._arg_index] = faiss.IndexFlatL2(len(self._embedding_function.embed_query(self._store_file)))
            if FaissVS._arg_index_to_docstore_id not in n_kwargs:
                n_kwargs[FaissVS._arg_index_to_docstore_id] = {}
            self._interface = FAISS(**n_kwargs)
        self.verify()

    def save(self):
        self._interface.save_local(folder_path = self._store_path, index_name = self._store_file)
