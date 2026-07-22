import re

from typing import Callable
from types import NoneType

from langchain_core.documents.base import Document
from sqlalchemy import create_engine, text

from qwshen.common.scheduling import ScheduleEvent
from qwshen.common.component import DocumentLoader
from qwshen.common.logging import RagLogger

class DbLoader(DocumentLoader):
    def __init__(self, kwargs: dict):
        super().__init__()

        self._connection = kwargs.get("connection", None)
        if self._connection is None:
            raise RuntimeError("The connection for DbLoader is not defined")
        self._table_name = kwargs.get("table_name", "")
        if self._table_name is None:
            raise RuntimeError("The table-name for DbLoader is not defined")

        columns = kwargs.get("columns", {})
        self._content_columns = columns.get("content", [])
        self._metadata_columns = columns.get("metadata", [])

        filter = kwargs.get("filter", {})
        self._ts_column = filter.get("ts_column", None)
        self._start_ts = filter.get("start_ts", None)
        self._end_ts = filter.get("end_ts", None)

    def load(self, handlerCallback: Callable[[list[Document], str], NoneType]):
        columns = self._content_columns + self._metadata_columns
        columns = "*" if len(columns) <= 0 else columns

        filter = ""
        if self._ts_column is not None and self._start_ts is not None and self._end_ts is not None:
            filter = f"{self._ts_column} >= '{self._start_ts}' and {self._ts_column} < '{self._end_ts}'"
        elif self._ts_column is not None and self._start_ts is not None:
            filter = f"{self._ts_column} >= '{self._start_ts}'"
        elif self._ts_column is not None and self._end_ts is not None:
            filter = f"{self._ts_column} < '{self._end_ts}'"
        filter = f"WHERE {filter}" if len(filter) > 0 else ""

        documents = []
        query = f"""SELECT {",".join(columns)} FROM {self._table_name} {filter}"""
        engine = create_engine(self._connection)        
        with engine.connect() as conn:
            rows = conn.execute(text(query)).mappings()
            columns = rows.keys() if len(columns) <= 0 else self._content_columns
            for row in rows:
                doc = Document(
                     page_content = "\r\n".join([f"{column}: {row[column]}" for column in columns]),
                     metadata = { column: row[column] for column in self._metadata_columns }
                )
                documents.append(doc)
        handlerCallback(documents, "")

    def on_event(self, event: dict, handlerCallback: Callable[[list[Document], str], NoneType]):
        e_type = event.get("event", None)
        kwargs = event.get("kwargs")
        if e_type == ScheduleEvent.TimeEvent:
            run_start_ts = kwargs.get("run_start_ts", None)
            run_end_ts = kwargs.get("run_end_ts", None)

            self._start_ts = run_start_ts.strftime("%Y-%m-%d %H:%M:%S") if run_start_ts is not None else None
            self._end_ts = run_end_ts.strftime("%Y-%m-%d %H:%M:%S") if run_end_ts is not None else None
            self.load(handlerCallback)
        else:
            RagLogger.logger().warning(f"FileLoader received an unknown event type [{e_type}] with arguments {kwargs}. The event will be ignored.")
