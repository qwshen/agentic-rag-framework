import re
from abc import abstractmethod
from typing import Iterator
from dataclasses import dataclass, field

from langchain_core.messages.ai import AIMessage  
from langchain_core.documents.base import Document
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_core.runnables import RunnableLambda, RunnableMap, RunnableSequence
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_agent
from langchain_core.retrievers import BaseRetriever

from definition.service import ServiceDef
from definition.types import Actor, ContextStore, Prompt, ChatModel, RetrievalActor, ContextStore, Retrieval, \
    ServicePrompt, ServiceContext, ServiceGeneration, ServiceAgentivity, ServicePromptWithHistory
from definition.service import Service, Search
from common.component import Runner
from common.component import Creator
from common.logging import RagLogger
from common.chat_history import BufferWindowConversionHistory, BufferWindowConversationSummaryHistory, ConversationHistory

class ServiceRunner(Runner):
    SESSION_ID: str = "session_id"

    def __init__(self, name: str):
        super().__init__(name)

    def _get_retriever(self, actor: RetrievalActor, store: ContextStore) -> VectorStoreRetriever:
        if actor.target_store != store.name:
            raise ValueError(f"Retrieval target store: {actor.target_store} does not match with context store: {store.name}")

        v_store = self._create(store.actor.type, store.actor.kwargs)
        return v_store.interface().as_retriever(search_type=actor.type, search_args=actor.kwargs)

    def process(self, user_query: str, kwargs: dict = {}) -> Iterator[Document]:
        pass
    
    def get_name(self):
        return self.name
    def get_long_name(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

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
    def __init__(self, prompt: Prompt, model: ChatModel, accept_answers: list[str], min_threshold_score: float = 0.6, max_iterations: int = 2):
        super().__init__(prompt, model)
        self.accept_answers = accept_answers
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
    def __init__(self, query_refinement: ServiceRethinkingAgent | None,
            document_grading: ServiceRethinkingAgent | None,answer_grounding: ServiceRethinkingAgent | None):
        self.query_refinement = query_refinement
        self.document_grading = document_grading
        self.answer_grounding = answer_grounding

class AgenticRetriever(BaseRetriever):
    def __init__(self, retrievers: list[VectorStoreRetriever], agent_model: ChatModel, 
                 query_refinement: ServiceRethinkingAgent=None, document_grading: ServiceReasoningAgent=None):
        super().__init__(tags=[])
        self._retriever = None
        self._agent = None
        if len(retrievers) == 0:
            raise ValueError("At least one retriever is required")
        elif len(retrievers) > 1 and agent_model is None:
            raise ValueError("Agent model is required when multiple retrievers are provided")
        elif len(retrievers) == 1:
            self._retriever = retrievers[0]
        else:
            self._agent = create_agent(
                model = Creator.create(agent_model.actor.type, agent_model.actor.kwargs),
                tools = retrievers
            )

        self._qr_variables = self._qr_prompt = self._qr_model = None
        if query_refinement is not None:
            self._qr_model = Creator.create(query_refinement.model.actor.type, query_refinement.model.actor.kwargs)
            self._qr_prompt, self._qr_variables = ContextServicePrompt.create(query_refinement.prompt.actor)

        self._dg_variables = self._dg_prompt = self._dg_model = None
        self._dg_accept_answers = self._dg_min_threshold_score = None 
        self._dg_max_iterations = None
        if document_grading is not None:
            self._dg_model = Creator.create(document_grading.model.actor.type, document_grading.model.actor.kwargs)
            self._dg_prompt, self._dg_variables = ContextServicePrompt.create(document_grading.prompt.actor)
            self._dg_accept_answers = document_grading.accept_answers
            self._dg_min_threshold_score = document_grading.min_threshold_score
            self._dg_max_iterations = document_grading.max_iterations

        self._document_grading_required = self._qr_prompt is not None and self._qr_model is not None and self._dg_prompt is not None and self._dg_model is not None

    def __fetch_relevant_documents(self, query: str):
        if self._agent:
            result = self._agent.run(query)
            if isinstance(result, list) and all(isinstance(x, Document) for x in result):
                return result
            else:
                return [Document(page_content=str(result))]
        elif self._retriever:
            return self._retriever._get_relevant_documents(query, run_manager=None) 

    def __grade_document_relevance(self, query: str, document: Document) -> bool:
        messages = self._dg_prompt.format_messages(**{
            self._dg_variables.var_question: query,
            self._dg_variables.var_document: document.page_content
        })
        response = re.sub(r"<think>.*?</think>", "", self._dg_model.invoke(messages).content.strip().lower(), flags=re.DOTALL)
        return any([answer.lower() in response for answer in self._dg_accept_answers])
    
    def rewrite_query(self, query: str, session_id: str) -> str:
        if self._qr_prompt is None or self._qr_model is None:
            return None, None
        chat_history = "\n\n".join([message.content for message in ConversationHistory.get_messages(session_id)])
        messages = self._qr_prompt.format_messages(**{
            self._qr_variables.var_question: query,
            self._qr_variables.var_history: chat_history
        })
        response = self._qr_model.invoke(messages).content.strip()
        RagLogger.logger().info(f"Rewritten query from: {query} to: {response}, for session_id: {session_id}")
        return response, chat_history
    
    def _get_relevant_documents(self, query: str, session_id: str):
        documents: list[Document] = []
        chat_history: str = ""
        cur_iteration = 0
        while True:
            documents = self.__fetch_relevant_documents(query)
            if not self._document_grading_required:
                break

            if cur_iteration >= self._dg_max_iterations:
                RagLogger.logger().info(f"Document grading reached max iterations: {self._dg_max_iterations} for query: {query}")
                break
            cur_iteration += 1
            relevant_score = sum([1 if self.__grade_document_relevance(query, document) else 0 for document in documents])
            if relevant_score / len(documents) >= self._dg_min_threshold_score:
                break
            rewrite_query, chat_history = self.rewrite_query(query, session_id)
            if rewrite_query is None:
                break
            query = rewrite_query
        return query, documents, chat_history

class AgenticGenerator:
    def __init__(self, rag_chain_with_source: RunnableSequence | RunnableWithMessageHistory, prompt_variables: PromptVariables, document_retriever: AgenticRetriever, 
            answer_grounding: ServiceReasoningAgent, answer_rewriting: ServiceRethinkingAgent):
        self._document_retriever = document_retriever
        self._prompt_variables = prompt_variables
        self._rag_chain_with_source = rag_chain_with_source

        self._ag_prompt = self._ag_variables = None
        self._ag_model = None
        self._ag_accept_answers = None
        self._ag_max_iterations = None
        if answer_grounding is not None:
            self._ag_model = Creator.create(answer_grounding.model.actor.type, answer_grounding.model.actor.kwargs)
            self._ag_prompt, self._ag_variables = ContextServicePrompt.create(answer_grounding.prompt.actor)
            self._ag_accept_answers = answer_grounding.accept_answers
            self._ag_max_iterations = answer_grounding.max_iterations
        self._answer_grounding_required = self._ag_prompt is not None and self._ag_model is not None

        self._ar_prompt = self._ar_variables = None
        self._ar_model = None
        if answer_rewriting is not None:
            self._ar_model = Creator.create(answer_rewriting.model.actor.type, answer_rewriting.model.actor.kwargs)
            self._ar_prompt, self._ar_variables = ContextServicePrompt.create(answer_rewriting.prompt.actor)
        self._answer_rewriting_required = self._ar_prompt is not None and self._ar_model is not None

    def invoke(self, user_query: str, session_id: str, kwargs: dict) -> Iterator[AIMessage]:
        cur_iteration = 0
        documents = chat_history = None
        cur_answer: AIMessage = None
        while True:
            user_query, documents, chat_history = self._document_retriever._get_relevant_documents(user_query, session_id)
            input = { 
                self._prompt_variables.var_question: user_query,
            }
            if self._prompt_variables.var_context is not None:
                input[self._prompt_variables.var_context] = "\n\n".join([document.page_content for document in documents])
            elif self._prompt_variables.var_document is not None:
                input[self._prompt_variables.var_document] = "\n\n".join([document.page_content for document in documents])
            if self._prompt_variables.var_history is not None:
                input[self._prompt_variables.var_history] = chat_history

            config = { ServiceRunner.SESSION_ID: session_id }
            if not self._answer_grounding_required and not self._answer_rewriting_required:
                for answer in self._rag_chain_with_source.stream(input=input, config=config, **kwargs):
                    yield answer
                break

            cur_answer = self._rag_chain_with_source.invoke(input=input, config=config, **kwargs)
            if not self._answer_grounding_required:
                break

            inputs = {
                self._ag_variables.var_question: user_query,
                self._ag_variables.var_answer: re.sub(r"<think>.*?</think>", "", cur_answer.content.strip(), flags=re.DOTALL)
            }
            if self._ag_variables.var_context is not None:
                inputs[self._ag_variables.var_context] = "\n\n".join([document.page_content for document in documents])
            elif self._ag_variables.var_document is not None:
                inputs[self._ag_variables.var_document] = "\n\n".join([document.page_content for document in documents])
            if self._ag_variables.var_history is not None:
                inputs[self._ag_variables.var_history] = chat_history
            grounding_score = re.sub(r"<think>.*?</think>", "", self._ag_model.invoke(self._ag_prompt.format_messages(**inputs)).content.strip().lower(), flags=re.DOTALL)
            if any([answer.lower() in grounding_score for answer in self._ag_accept_answers]):
                break

            cur_iteration += 1
            if cur_iteration >= self._ag_max_iterations:
                RagLogger.logger().info(f"Answer grounding reached max iterations: {self._ag_max_iterations} for query: {user_query}")
                break
            rewritten_query, _ = self._document_retriever.rewrite_query(user_query, session_id)
            if rewritten_query is None:
                break
            RagLogger.logger().info(f"Rewriting query for answer grounding from: {user_query} to: {rewritten_query}, for session_id: {session_id}")
            user_query = rewritten_query

        if self._answer_rewriting_required and cur_answer is not None:
            inputs = {                
                self._ar_variables.var_answer: re.sub(r"<think>.*?</think>", "", cur_answer.content.strip(), flags=re.DOTALL)
            }
            if self._ar_variables.var_question is not None:
                inputs[self._ar_variables.var_question] = user_query
            if self._ar_variables.var_context is not None:
                inputs[self._ar_variables.var_context] = "\n\n".join([document.page_content for document in documents]) if documents is not None else ""
            elif self._ar_variables.var_document is not None:
                inputs[self._ar_variables.var_document] = "\n\n".join([document.page_content for document in documents]) if documents is not None else ""
            if self._ar_variables.var_history is not None:
                inputs[self._ar_variables.var_history] = chat_history if chat_history is not None else ""
            cur_answer = self._ar_model.invoke(self._ar_prompt.format_messages(**inputs))
        yield cur_answer

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
        self._document_retriever = AgenticRetriever(agent_retrievers, agent_model, self._agentivity.query_refinement, self._agentivity.document_grading)
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
            generator = AgenticGenerator(
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
                yield { "metadata": document.metadata }
                yield { "answer": document.page_content }

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
        else:
            RagLogger.logger().info(f"Setting up answer rewriting with prompt: {generation.answer_rewriting.ref_prompt} and model: {generation.answer_rewriting.ref_model}, for {self.name}")
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
        else:
            RagLogger.logger().info(f"Setting up answer grounding with prompt: {agentivity.answer_grounding.ref_prompt} and model: {agentivity.answer_grounding.ref_model}, for {self.name}")
        answer_grounding = ServiceReasoningAgent(
            prompt=answer_grounding_prompt, 
            model=answer_grounding_model,
            accept_answers=agentivity.answer_grounding.accept_groundedness_answers, 
            max_iterations=agentivity.answer_grounding.max_iterations
        ) if answer_grounding_prompt is not None and answer_grounding_model is not None else None

        document_grading_prompt = self._prompts.get(agentivity.document_grading.ref_prompt, None)
        document_grading_model = self._models.get(agentivity.document_grading.ref_model, None)
        if (document_grading_prompt is not None and document_grading_model is None) or (document_grading_prompt is None and document_grading_model is not None):
            raise ValueError(f"Both prompt and model are required for document grading agentivity.")
        else:
            RagLogger.logger().info(f"Setting up document grading with prompt: {agentivity.document_grading.ref_prompt} and model: {agentivity.document_grading.ref_model}, for {self.name}")
        document_grading = ServiceReasoningAgent(
            prompt=document_grading_prompt, 
            model=document_grading_model,
            accept_answers=agentivity.document_grading.accept_gradedness_answers, 
            min_threshold_score=agentivity.document_grading.min_threshold_score,
            max_iterations=agentivity.document_grading.max_iterations
        ) if document_grading_prompt is not None and document_grading_model is not None else None

        query_refinement_prompt = self._prompts.get(agentivity.query_refinement.ref_prompt, None)
        query_refinement_model = self._models.get(agentivity.query_refinement.ref_model, None)
        if (query_refinement_prompt is not None and query_refinement_model is None) or (query_refinement_prompt is None and query_refinement_model is not None):
            raise ValueError(f"Both prompt and model are required for query refinement agentivity.")
        else:
            RagLogger.logger().info(f"Setting up query refinement with prompt: {agentivity.query_refinement.ref_prompt} and model: {agentivity.query_refinement.ref_model}, for {self.name}")
        query_refinement = ServiceRethinkingAgent(
            prompt=query_refinement_prompt, 
            model=query_refinement_model
        ) if query_refinement_prompt is not None and query_refinement_model is not None else None

        return ContextServiceAgentivity(query_refinement, document_grading, answer_grounding)

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