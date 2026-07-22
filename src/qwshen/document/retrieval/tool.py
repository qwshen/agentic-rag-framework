from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import Tool

class RetrievalTool(ABC):
    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description

    @abstractmethod
    def get_tool(): Tool

    def parse_schema_for_query(self) -> str:
        tool = self.get_tool()
        if tool.args_schema:
            schema = tool.args_schema.model_json_schema()
            fields = schema.get("required", [])
            if len(fields) == 0:
                return None
            elif len(fields) == 1:
                return fields[0]
            else:
                raise ValueError("Should only one property for user-query.")
        else:
            return None

    @abstractmethod
    def parse_result(self, result: Any): list[str]

