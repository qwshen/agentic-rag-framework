from langchain_core.tools import Tool
from langchain_core.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import VectorStoreRetriever
from typing import Any

from qwshen.definition.types import ContextStore
from qwshen.document.retrieval.tool import RetrievalTool
from qwshen.common.component import Creator

class VSRetriever(RetrievalTool, Creator):
    def __init__(self, name: str, description: str, document_store: ContextStore, search_type: str, search_kwargs: dict):
        super().__init__(name, description)

        v_store = self._create(document_store.actor.type, document_store.actor.kwargs)
        self._vs = v_store.interface().as_retriever(search_type=search_type, search_kwargs=search_kwargs)

    def get_retriever(self) -> VectorStoreRetriever:
        return self._vs

    def get_tool(self) -> Tool:
        return create_retriever_tool(self._vs, name=self._name, description=self._description)

    def parse_result(self, result: Any) -> list[str]:
        return [result.strip()] if result is not None and len(result.strip()) > 0 else []
