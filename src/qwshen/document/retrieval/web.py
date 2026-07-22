from langchain_core.tools import Tool
from langchain_core.tools.retriever import create_retriever_tool
from typing import Any

from qwshen.document.retrieval.tool import RetrievalTool
from qwshen.common.component import Creator

class TavilyRetriever(RetrievalTool):
    def __init__(self, name: str, description: str, worker_type: str, worker_kwargs: dict):
        super().__init__(name, description)        
        self._engine = Creator.create(worker_type, worker_kwargs)

    def get_tool(self) -> Tool:
        return Tool(name=self._name, description=self._description, func=self._engine.invoke)

    def parse_result(self, result: Any) -> list[str]:        
        return [f"""{rs["title"]}\n\n{rs["content"]}""" for rs in result["results"]] if result is not None and "results" in result else []
