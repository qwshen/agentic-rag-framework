from queue import Queue, Empty
from threading import Thread, Lock, current_thread
import time
from types import NoneType
from functools import reduce

from langchain_core.documents.base import Document

from common.component import Creator, Runner, DocumentHandler, DocumentIndexer
from common.scheduling import ScheduleEvent, Scheduler
from common.logging import RagLogger
from common.utils import nvl
from definition.types import ContextStore, LoadActor, SplitActor, StoreActor, IndexActor
from definition.index import IndexDef

class DocumentCoordinator(DocumentHandler):
    def __init__(self, output_queues: list[Queue], operatorsCount: int):
        super().__init__(output_queues)

        self._operatorsCount = operatorsCount
        self._doneCount = 0
        self._doneLocker = Lock()

    def documents_arrived(self, documents: list[Document], source: str, done: bool = False) -> NoneType:
        documents = nvl(documents, [])
        if len(documents) > 0:
            for batch_documents in self.batch_documents(documents):
                self.queue(batch_documents, source, done)

            docs_size = reduce(lambda x, y: x + y, [len(document.page_content) for document in documents], 0)
            docs_count = len(documents)
            RagLogger.logger().info(f"{current_thread().name}-{source} --> {docs_count} documents [{docs_size} bytes] loaded")

        if done:
            with self._doneLocker:
                self._doneCount += 1
                if self._doneCount >= self._operatorsCount:
                    self.queue([], "N/A", True)
            RagLogger.logger().debug(f"{current_thread().name} --> {len(documents) if documents is not None else 0} documents from {source} queued with done = {done}")

class DocumentLoadHandler(Runner):
    def __init__(self, name: str, actor: LoadActor, scheduler: Scheduler, coordinator: DocumentCoordinator):
        super().__init__(name)

        self._scheduler = scheduler
        if self._scheduler is not None:
            self._scheduler.add_callback(self._execute)
        self._document_loader = self._create(actor.type, actor.kwargs)
        self._coordinator = coordinator

    def _execute(self, event: ScheduleEvent, kwargs: dict):
        self._run(e = {"event": event, "kwargs": kwargs})

    def _run(self, e: dict):
        RagLogger.logger().info(f"{self.name} --> Starting documents loading ...")
        self._document_loader.load(self._coordinator.documents_arrived) if e is None else self._document_loader.on_event(e, self._coordinator.documents_arrived)

    def run(self):
        if self._scheduler is not None:
            RagLogger.logger().info(f"{self.name} --> Starting scheduler for document loading ...")
            self._scheduler.run()
        else:
            RagLogger.logger().info(f"{self.name} --> No scheduler defined for document loading, running immediately ...")
            self._run(None)
            self._coordinator.documents_arrived([], "N/A", True)

class DocumentSplitHandler(Runner):
    def __init__(self, name: str, actor: SplitActor, input_queue: Queue, coordinator: DocumentCoordinator):
        super().__init__(name)

        self._splitter = self._create(actor.type, actor.kwargs)
        self._input_queue = input_queue
        self._coordinator = coordinator

    def run(self):
        RagLogger.logger().info(f"{self.name} --> Start documents splitting ...")
        while True:
            try:
                documents, source, done = self._input_queue.get(True, 3)
                RagLogger.logger().debug(f"{self.name} --> {len(documents) if documents is not None else 0} documents received from {source} with done = {done}")
                if documents is not None and len(documents) > 0:
                    new_documents = self._splitter.split(documents)
                    self._coordinator.documents_arrived(new_documents, source, done)
                if done:
                    self._coordinator.documents_arrived([], "N/A", True)
                    break
            except Empty:
                time.sleep(1)

class DocumentIndexHandler(Runner):
    def __init__(self, name: str, actor: StoreActor, input_queue: Queue):
        DocumentHandler.__init__(self, [])
        Runner.__init__(self, name)

        self._indexer = DocumentIndexer(self._create(actor.type, actor.kwargs))
        self._input_queue = input_queue

    def run(self):
        RagLogger.logger().info(f"{self.name} --> Start documents indexing ...")
        while True:
            try:
                documents, source, done = self._input_queue.get(True, 3)
                RagLogger.logger().debug(f"{self.name} --> {len(documents) if documents is not None else 0} documents received from {source} with done = {done}")
                if documents is not None and len(documents) > 0:
                    ids = self._indexer.add_documents(documents)
                    self._indexer.save()

                    input_docs_count = len(documents)
                    input_docs_size = reduce(lambda x, y: x + y, [len(document.page_content) for document in documents], 0)
                    output_records_count = len(ids)
                    s_msg = f"{input_docs_count} documents [{input_docs_size} bytes] indexed into {output_records_count} records"
                    RagLogger.logger().info(f"{self.name}-{source} --> {s_msg}")
                if done:
                    break
            except Empty:
                time.sleep(1)

class DocumentOperator(Runner):
    def __init__(self, index_actor: IndexActor, context_stores: list[ContextStore]):
        super().__init__(index_actor.name)
        
        self._index_name = index_actor.name
        self._runners = []

        ls_doc_queues = [Queue() for _ in range(index_actor.splitter.concurrency.workers)]
        sv_doc_queues = [Queue() for _ in range(index_actor.indexer.concurrency.workers)]

        loadCoordinator = DocumentCoordinator(ls_doc_queues, len(index_actor.loaders))
        schedulers = {}
        for idx, loader in enumerate(index_actor.loaders):
            if loader.scheduler is not None:
                id = loader.scheduler.id()
                if id not in schedulers:
                    schedulers[id] = Creator.create(loader.scheduler.type, loader.scheduler.kwargs)
            scheduler = schedulers.get(loader.scheduler.id()) if loader.scheduler is not None else None
            self._runners.append(DocumentLoadHandler(f"{self._index_name}.loader-{idx}", loader.actor, scheduler, loadCoordinator))

        splitCoordinator = DocumentCoordinator(sv_doc_queues, len(ls_doc_queues))
        for idx in range(len(ls_doc_queues)):
            self._runners.append(DocumentSplitHandler(f"{self._index_name}.splitter-{idx}", index_actor.splitter.actor, ls_doc_queues[idx], splitCoordinator))

        for idx in range(len(sv_doc_queues)):
            context_store = [store for store in context_stores if store.name == index_actor.indexer.document_store]
            if len(context_store) != 1:
                raise ValueError(f"Context store not found for {index_actor.indexer.document_store}")
            self._runners.append(DocumentIndexHandler(f"{self._index_name}.indexer-{idx}", context_store[0].actor, sv_doc_queues[idx]))

    def run(self):
        threads = [Thread(target=runner.run, name=runner.name) for runner in self._runners]
        for thread in threads:
            thread.start()
            RagLogger.logger().info(f"{self.name} --> Starting {thread.name}")
        for thread in threads:
            thread.join()

    @staticmethod
    def setup(index_def: IndexDef) -> list[Runner]:
        return [DocumentOperator(actor, index_def.context_stores) for actor in index_def.actors]
            
