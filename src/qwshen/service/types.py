from abc import abstractmethod
from typing import Iterator
from dataclasses import dataclass

from langchain_core.documents.base import Document

from qwshen.common.component import Creator
from qwshen.common.component import Runner
from qwshen.definition.types import Actor, ContextStore, Prompt, ChatModel, ContextStore, Retrieval, ServicePromptWithHistory, RetrievalActor
from langchain_core.vectorstores.base import VectorStoreRetriever

class ServiceRetrieval:
    def __init__(self, retrieval: Retrieval, store: ContextStore):
        self.retrieval = retrieval
        self.store = store

class ServiceRetrievalAgent:
    def __init__(self, retrievals: list[ServiceRetrieval], agent_model: ChatModel):
        self.retrievals = retrievals
        self.agent_model = agent_model

    def get_name(self):
        names = [f"{retrieval.retrieval.name} with store: {retrieval.store.name}" for retrieval in self.retrievals]
        return ", ".join(names)
    
class ServiceRethinkingAgent:
    def __init__(self, prompt: Prompt, model: ChatModel):
        self.prompt = prompt
        self.model = model

class ServiceReasoningAgent(ServiceRethinkingAgent):
    def __init__(self, prompt: Prompt, model: ChatModel, accept_answers: list[str], reject_answers: list[str], min_threshold_score: float = 0.6, max_iterations: int = 2):
        super().__init__(prompt, model)
        self.accept_answers = accept_answers
        self.reject_answers = reject_answers
        self.min_threshold_score = min_threshold_score
        self.max_iterations = max_iterations

@dataclass(frozen=True) 
class PromptVariables:
    var_question: str = "question"
    var_context: str = "context"
    var_document: str = "document"
    var_history: str = "chat_history"
    var_answer: str = "answer"

class ContextServicePrompt:
    def __init__(self, prompt: Prompt, with_history: ServicePromptWithHistory):
        self.prompt = prompt
        self.with_history = with_history

    @staticmethod
    def create( actor:Actor):
        prompt_template = Creator.create(actor.type, actor.kwargs)
        var_question = var_history = var_context = var_documents = var_answer = None
        for var_name in prompt_template.input_variables:
            if "question" in var_name.lower() or "query" in var_name.lower():
                var_question = var_name
            elif "history" in var_name.lower():
                var_history = var_name
            elif "context" in var_name.lower():
                var_context = var_name
            elif "document" in var_name.lower():
                var_documents = var_name
            elif "answer" in var_name.lower() or "response" in var_name.lower() or "output" in var_name.lower():
                var_answer = var_name
            else:
                raise ValueError(f"Unknown variable: {var_name} in prompt template. variable must contain one of the following keys - question/query, history, context, document, answer/response/output.")
        return (prompt_template, PromptVariables(var_question=var_question, var_history=var_history, var_context=var_context, var_document=var_documents, var_answer=var_answer))
    
class ContextServiceGeneration:
    def __init__(self, model: ChatModel, answer_rewriting: ServiceRethinkingAgent | None = None):
        self.model = model
        self.answer_rewriting = answer_rewriting

class ContextServiceAgentivity:
    def __init__(self, query_refining: ServiceRethinkingAgent | None,
            document_grading: ServiceRethinkingAgent | None,answer_grounding: ServiceRethinkingAgent | None):
        self.query_refining = query_refining
        self.document_grading = document_grading
        self.answer_grounding = answer_grounding

class ServiceRunner(Runner):
    SESSION_ID: str = "session_id"

    def __init__(self, name: str):
        super().__init__(name)

    def _get_retriever(self, actor: RetrievalActor, store: ContextStore) -> VectorStoreRetriever:
        if actor.target_store != store.name:
            raise ValueError(f"Retrieval target store: {actor.target_store} does not match with context store: {store.name}")

        v_store = self._create(store.actor.type, store.actor.kwargs)
        return v_store.interface().as_retriever(search_type=actor.type, search_kwargs=actor.kwargs)

    def process(self, user_query: str, kwargs: dict = {}) -> Iterator[Document]:
        pass
    
    def get_name(self):
        return self.name
    def get_long_name(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

