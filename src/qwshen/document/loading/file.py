import re

from typing import Callable
from types import NoneType
from datetime import datetime
from functools import reduce
from os import listdir, path
from os.path import isfile, isdir, join

from langchain_core.documents.base import Document

from qwshen.common.component import Creator
from qwshen.common.scheduling import ScheduleEvent
from qwshen.common.component import DocumentLoader
from qwshen.common.logging import RagLogger
from qwshen.common.utils import is_file_ready

class FileLoader(DocumentLoader):
    def __init__(self, kwargs: dict):
        super().__init__()

        self._directory = kwargs.get("directory", None)
        if self._directory is None:
            raise RuntimeError("The directory for FileLoader is not defined")
        self._file_extensions = re.split("[,;]", kwargs.get("file_extensions", ""))
        self._recursive = kwargs.get("recursive", False)

        worker = kwargs.get("worker", None)
        if worker is None:
            raise RuntimeError("The worker is not defined for FileLoader")
        self._worker_type = worker.get("type", None)
        if self._worker_type is None:
            raise RuntimeError("The work-type for FileLoader is not defined")
        self._worker_kwargs = worker.get("kwargs", {})

    def load(self, handlerCallback: Callable[[list[Document], str], NoneType]):
        for document_file in FileLoader._collectFiles(self._directory, self._file_extensions, self._recursive):
            documents = Creator.create(self._worker_type, self._worker_kwargs | { "file_path": document_file }).load()
            handlerCallback(documents, document_file)

    def on_event(self, event: dict, handlerCallback: Callable[[list[Document], str], NoneType]):
        e_type = event.get("event", None)
        kwargs = event.get("kwargs")
        if e_type == ScheduleEvent.FileEvent:
            file_path = kwargs.get("file_path", None)
            if file_path is not None:
                dir, file = path.split(file_path)
                if ((self._recursive and dir.startswith(self._directory)) or (not self._recursive and dir == self._directory)) and FileLoader._file_ext_match(file, self._file_extensions):
                    documents = Creator.create(self._worker_type, self._worker_kwargs | { "file_path": file_path }).load()
                    handlerCallback(documents, file_path)
        elif e_type == ScheduleEvent.TimeEvent:
            run_start_ts = kwargs.get("run_start_ts", None)
            run_end_ts = kwargs.get("run_end_ts", None)
            if run_start_ts is None and run_end_ts is None:
                self.load(handlerCallback)
            else:
                for document_file in FileLoader._collectFiles(self._directory, self._file_extensions, self._recursive):
                   if FileLoader._file_ts_match(document_file, run_start_ts, run_end_ts):
                       documents = Creator.create(self._worker_type, self._worker_kwargs | { "file_path": document_file }).load()
                       handlerCallback(documents, document_file)
        else:
            RagLogger.logger().warning(f"FileLoader received an unknown event type [{e_type}] with arguments {kwargs}. The event will be ignored.")

    @staticmethod
    def _file_ext_match(file_name: str, file_extensions: list[str]) -> bool:
        return reduce(lambda x, y: x | y, [True if fe in ["", "*"] else file_name.lower().endswith(fe.lower()) for fe in file_extensions])

    @staticmethod
    def _file_ts_match(file_path: str, start_dt: datetime, end_dt: datetime) -> bool:
        file_dt = max(datetime.fromtimestamp(path.getctime(file_path)), datetime.fromtimestamp(path.getmtime(file_path)))
        return (True if start_dt is None else file_dt >= start_dt) and (True if end_dt is None else file_dt < end_dt)

    @staticmethod
    def _collectFiles(directory: str, file_extensions: list[str], recursive: bool) -> list[str]:
        paths = listdir(directory)
        files = {}
        for path in paths:
            full_path = join(directory, path)
            if isfile(full_path) and FileLoader._file_ext_match(path, file_extensions) and is_file_ready(full_path):
               files |= { path: directory }
            elif isdir(full_path) and recursive:
               files |= FileLoader._collectFiles(full_path, file_extensions, recursive)
        return [join(directory, path) for path, directory in files.items()]

      
    
