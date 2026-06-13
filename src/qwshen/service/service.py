from typing import Iterator

from langchain_core.documents.base import Document
from langchain_core.runnables import RunnableLambda, RunnableMap

from qwshen.definition.types import ContextStore, Prompt, ChatModel, ContextStore, Retrieval, ServicePrompt, ServiceContext, \
    ServiceGeneration, ServiceAgentivity
from qwshen.definition.service import ServiceDef
from qwshen.definition.service import Service, Search
from qwshen.common.component import Runner
from qwshen.common.component import Creator
from qwshen.common.logging import RagLogger
from qwshen.common.chat_history import BufferWindowConversionHistory, BufferWindowConversationSummaryHistory

from .types import ServiceRetrieval, ServiceRetrievalAgent, ServiceRethinkingAgent, ServiceReasoningAgent, ContextServicePrompt, \
    ContextServiceGeneration, ContextServiceAgentivity, ServiceRunner
from .retrieval import AgenticRetriever
from .completion import AgenticCompletion

class ContextService(ServiceRunner):
    def __init__(self, name: str, prompt: ContextServicePrompt, retrieval: ServiceRetrievalAgent, generation: ContextServiceGeneration, agentivity: ContextServiceAgentivity | None = None):
        super().__init__(name)

        self._prompt = prompt
        self._retrieval = retrieval
        self._generation = generation
        self._agentivity = agentivity
        
        self._rag_chain_with_source = None
        self._prompt_variables = None
        self._document_retriever = None

    def run(self):
        prompt_template, self._prompt_variables = ContextServicePrompt.create(self._prompt.prompt.actor)
        if self._prompt.with_history.enabled and self._prompt_variables.var_history is None:
            raise ValueError(f"Prompt: {self._prompt.prompt.name} requires history variable but not found in input variables.")
        RagLogger.logger().info(f"prompt template used: {self._prompt.prompt.name}, for {self.name} with variables: {self._prompt_variables.var_question}, {self._prompt_variables.var_history}, {self._prompt_variables.var_context}")

        chat_model = Creator.create(self._generation.model.actor.type, self._generation.model.actor.kwargs)
        RagLogger.logger().info(f"chat-model used: {self._generation.model.name}, for {self.name}")
        
        agent_retrievers = [self._get_retriever(retrieval.retrieval.search, retrieval.store) for retrieval in self._retrieval.retrievals]
        agent_model = self._retrieval.agent_model if self._retrieval.agent_model is not None else self._generation.model
        if len(agent_retrievers) == 0:
            raise ValueError("At least one retriever is required")
        self._document_retriever = AgenticRetriever(agent_retrievers, agent_model, self._agentivity.query_refining, self._agentivity.document_grading)
        RagLogger.logger().info(f"retrievel used: {self._retrieval.get_name()}, for {self.name}")

        rag_chain_map = {
            self._prompt_variables.var_context: RunnableLambda(lambda input, run_manager = None: input[self._prompt_variables.var_context]),
            self._prompt_variables.var_question: RunnableLambda(lambda input, run_manager = None: input[self._prompt_variables.var_question])
        } 
        if self._prompt_variables.var_history is not None:
            rag_chain_map[self._prompt_variables.var_history] = RunnableLambda(lambda input, run_manager = None: input[self._prompt_variables.var_history])
            rag_chain = RunnableMap(rag_chain_map) | prompt_template | chat_model
            (use_summary, window_k) = (self._prompt.with_history.use_summary, self._prompt.with_history.window_k) if self._prompt.with_history is not None else (False, 9)
            if use_summary:
                self._rag_chain_with_source = BufferWindowConversationSummaryHistory.create_chain_with_history(
                    rag_chain,                     
                    self._prompt_variables.var_question, self._prompt_variables.var_history, 
                    chat_model, self._prompt.with_history.window_k
                )
                RagLogger.logger().info(f"Using summary history with k={window_k} for {self.name}")
            else:
                self._rag_chain_with_source = BufferWindowConversionHistory.create_chain_with_history(
                    rag_chain, 
                    self._prompt_variables.var_question, self._prompt_variables.var_history, 
                    self._prompt.with_history.window_k
                )
                RagLogger.logger().info(f"Using window history with k={window_k} for {self.name}")
        else:
            self._rag_chain_with_source = RunnableMap(rag_chain_map) | prompt_template | chat_model

    def process(self, user_query: str, kwargs: dict = {}) -> Iterator[Document]:
        RagLogger.logger().info(f"Processing user-query: {user_query}, with {self.name}")
        if self._rag_chain_with_source is None:
            raise RuntimeError(f"Service: {self.name} is not started yet.")
        elif ServiceRunner.SESSION_ID not in kwargs:
            raise ValueError(f"{ServiceRunner.SESSION_ID} is required in kwargs for processing.")
        try:
            session_id = kwargs.pop(ServiceRunner.SESSION_ID)
            generator = AgenticCompletion(
                rag_chain_with_source=self._rag_chain_with_source, 
                prompt_variables=self._prompt_variables, document_retriever=self._document_retriever, 
                answer_grounding=self._agentivity.answer_grounding, answer_rewriting=self._generation.answer_rewriting
            )
            return generator.invoke(user_query, session_id, kwargs)
        except Exception as e:
            RagLogger.logger().error(f"Error occurred while processing request for question: {user_query} with error: {e}")
            raise e
        
    def get_long_name(self):
        return f"{self.name} - {self._generation.get_name()} with {self._prompt.name} and {self._retrieval.name}"


class SearchService(ServiceRunner):
    def __init__(self, name: str, retrieval: Retrieval, store: ContextStore):
        super().__init__(name)

        if retrieval.search.target_store != store.name:
            raise ValueError(f"Retrieval target store: {retrieval.search.target_store} does not match with context store: {store.name}")
        self._retrieval = retrieval
        self._store = store
        self._document_retriever = None

    def run(self):
        RagLogger.logger().info(f"retrievel used: {self._retrieval.name} with store: {self._store.name}, for {self.name}")
        document_retriever = self._get_retriever(self._retrieval.search, self._store)
        self._document_retriever = document_retriever

    def process(self, user_query: str, kwargs: dict = {}) -> Iterator[Document]:
        RagLogger.logger().info(f"Processing user-query: {user_query}, with {self.name}")
        for documents in self._document_retriever.stream(user_query, **kwargs):
            for document in documents:
                yield document

    def get_long_name(self):
        return f"{self.name} - search with {self._retrieval.name}"
    
class ServiceOperator(Runner):
    def __init__(self, context_stores: list[ContextStore], prompts: list[Prompt], models: list[ChatModel], retrievals: list[Retrieval]):
        super().__init__("service-operator")
        self._context_stores = dict([(context_store.name, context_store) for context_store in context_stores])
        self._prompts = dict([(prompt.name, prompt) for prompt in prompts])
        self._models = dict([(model.name, model) for model in models])
        self._retrievals = dict([(retrieval.name, retrieval) for retrieval in retrievals])

    def _setup_service(self, service: Service) -> ServiceRunner:
        if service.definition.prompt.ref_prompt not in self._prompts:
            raise ValueError(f"Prompt: {service.definition.prompt.ref_prompt} is not defined.")
        elif not all([ref_retrieval in self._retrievals for ref_retrieval in service.definition.context.ref_retrievals]):
            raise ValueError(f"Retrieval: {service.definition.context.ref_retrievals} is not defined.")
        elif service.definition.generation.ref_model not in self._models:
            raise ValueError(f"Chat-Model: {service.definition.generation.ref_model} is not defined.")

        prompt = self._prepare_prompt(service.definition.prompt)
        retrieval_agent = self._prepare_retrieval_agent(service.definition.context)
        generation = self._prepare_generation(service.definition.generation)
        agentivity = self._prepare_agentivity(service.definition.agentivity) if service.definition.agentivity is not None else None
        return ContextService(service.name, prompt, retrieval_agent, generation, agentivity)

    def _prepare_prompt(self, prompt: ServicePrompt) -> ContextServicePrompt:
        return ContextServicePrompt(self._prompts.get(prompt.ref_prompt), prompt.with_history)

    def _prepare_generation(self, generation: ServiceGeneration) -> ContextServiceGeneration:
        model = self._models[generation.ref_model]
        rewriting_prompt = self._prompts.get(generation.answer_rewriting.ref_prompt, None)
        rewriting_model = self._models.get(generation.answer_rewriting.ref_model, None)
        if (rewriting_prompt is not None and rewriting_model is None) or (rewriting_prompt is None and rewriting_model is not None):
            raise ValueError(f"Both prompt and model are required for answer rewriting.")
        elif rewriting_prompt is not None and rewriting_model is not None:
            RagLogger.logger().info(f"Setting up answer rewriting with prompt: {rewriting_prompt} and model: {rewriting_model}, for {self.name}")
        rethinkingAgent = None if rewriting_prompt is None or rewriting_model is None else ServiceRethinkingAgent(rewriting_prompt, rewriting_model)
        return ContextServiceGeneration(model, rethinkingAgent)

    def _prepare_retrieval_agent(self, context: ServiceContext) -> ServiceRetrievalAgent:
        retrievals = [self._prepare_retrieval(retrieval_name) for retrieval_name in context.ref_retrievals]
        agent_model = self._models.get(context.agent.ref_model, None)
        return ServiceRetrievalAgent(retrievals, agent_model)

    def _prepare_agentivity(self, agentivity: ServiceAgentivity) -> ContextServiceAgentivity:
        answer_grounding_prompt = self._prompts.get(agentivity.answer_grounding.ref_prompt, None)
        answer_grounding_model = self._models.get(agentivity.answer_grounding.ref_model, None)
        if (answer_grounding_prompt is not None and answer_grounding_model is None) or (answer_grounding_prompt is None and answer_grounding_model is not None):
            raise ValueError(f"Both prompt and model are required for answer grounding agentivity.")
        elif answer_grounding_prompt is not None and answer_grounding_model is not None:
            RagLogger.logger().info(f"Setting up answer grounding with prompt: {answer_grounding_prompt} and model: {answer_grounding_model}, for {self.name}")
        answer_grounding = ServiceReasoningAgent(
            prompt=answer_grounding_prompt, 
            model=answer_grounding_model,
            accept_answers=agentivity.answer_grounding.accept_groundedness_answers, 
            reject_answers=agentivity.answer_grounding.reject_groundedness_answers,
            max_iterations=agentivity.answer_grounding.max_iterations
        ) if answer_grounding_prompt is not None and answer_grounding_model is not None else None

        document_grading_prompt = self._prompts.get(agentivity.document_grading.ref_prompt, None)
        document_grading_model = self._models.get(agentivity.document_grading.ref_model, None)
        if (document_grading_prompt is not None and document_grading_model is None) or (document_grading_prompt is None and document_grading_model is not None):
            raise ValueError(f"Both prompt and model are required for document grading agentivity.")
        elif document_grading_prompt is not None and document_grading_model is not None:
            RagLogger.logger().info(f"Setting up document grading with prompt: {document_grading_prompt} and model: {document_grading_model}, for {self.name}")
        document_grading = ServiceReasoningAgent(
            prompt=document_grading_prompt, 
            model=document_grading_model,
            accept_answers=agentivity.document_grading.accept_gradedness_answers, 
            reject_answers=agentivity.document_grading.reject_gradedness_answers,
            min_threshold_score=agentivity.document_grading.min_threshold_score,
            max_iterations=agentivity.document_grading.max_iterations
        ) if document_grading_prompt is not None and document_grading_model is not None else None

        query_refining_prompt = self._prompts.get(agentivity.query_refining.ref_prompt, None)
        query_refining_model = self._models.get(agentivity.query_refining.ref_model, None)
        if (query_refining_prompt is not None and query_refining_model is None) or (query_refining_prompt is None and query_refining_model is not None):
            raise ValueError(f"Both prompt and model are required for query refining agentivity.")
        elif query_refining_prompt is not None and query_refining_model is not None:
            RagLogger.logger().info(f"Setting up query refining with prompt: {query_refining_prompt} and model: {query_refining_model}, for {self.name}")
        query_refining = ServiceRethinkingAgent(
            prompt=query_refining_prompt, model=query_refining_model
        ) if query_refining_prompt is not None and query_refining_model is not None else None

        return ContextServiceAgentivity(query_refining, document_grading, answer_grounding)

    def _setup_search(self, search: Search) -> ServiceRunner:
        if search.definition.retrieval not in self._retrievals:
            raise ValueError(f"Retrieval: {search.definition.retrieval} is not defined.")
       
        serviceRetrieval = self._prepare_retrieval(search.definition.retrieval)
        return SearchService(search.name, serviceRetrieval.retrieval, serviceRetrieval.store)

    def _prepare_retrieval(self, rerieval_name: str) -> ServiceRetrieval:
        retrieval = self._retrievals.get(rerieval_name)
        stores = [store for store in self._context_stores.values() if store.name == retrieval.search.target_store]
        if len(stores) != 1:
            raise ValueError(f"Context store not found for {retrieval.search.target_store}")
        return ServiceRetrieval(retrieval, stores[0])
    
    @staticmethod
    def setup(service_def: ServiceDef) -> list[Runner, list[str]]:
        cs = ServiceOperator(context_stores=service_def.context_stores, prompts=service_def.prompts, models=service_def.chat_models, retrievals=service_def.retrievals)
        contextServices = [(cs._setup_service(service), service.access_roles) for service in service_def.services]
        searchServices = [(cs._setup_search(search), search.access_roles) for search in service_def.searches]
        return contextServices + searchServices

    @staticmethod
    def is_context_service(runner: ServiceRunner) -> bool:
        return isinstance(runner, ContextService)

    @staticmethod
    def is_search_service(runner: ServiceRunner) -> bool:
        return isinstance(runner, SearchService)