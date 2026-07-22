import re
from typing import ClassVar
from langchain_core.documents.base import Document
from langchain.agents import create_agent
from langchain_core.retrievers import BaseRetriever

from qwshen.definition.types import ChatModel
from qwshen.common.component import Creator
from qwshen.common.logging import RagLogger
from qwshen.common.chat_history import ConversationHistory
from qwshen.service.types import ServiceRethinkingAgent, ServiceReasoningAgent, ContextServicePrompt
from qwshen.document.retrieval.tool import RetrievalTool

class AgenticRetriever(BaseRetriever):
    THINKING_RGX: ClassVar[str] = r"<\s*(think|thinking|analysis|reasoning|chain_of_thought|scratchpad|thoughts|deliberation|internal|hidden|steps|plan|logic)\s*>.*?<\s*/\s*\1\s*>"
    ANSWER_RGXs: ClassVar[list[str]] = [
        r"""[\W_]*["']?(?:answer|final answer|conclusion|result|output|label|prediction|class|verdict|decision)["']?[\W_]*\s*:\s*[\W_]*["']?([A-Za-z0-9-]+)["']?[\W_]*""",
        r"""```(?:ans|answer|final|result|output|label|class|prediction|verdict|conclusion|decision)\s*\n\s*([A-Za-z0-9-]+)\s*\n```"""
    ]

    def __init__(self, retrievers: list[RetrievalTool], agent_model: ChatModel, fallback_retriever: RetrievalTool,
                 query_refining: ServiceRethinkingAgent=None, document_grading: ServiceReasoningAgent=None):
        super().__init__(tags=[])
        self._agent = self._fallback_agent = None
        self._retrieval_tool = self._fallback_tool = None
        self._retrieval_field = self._fallback_field = None
        if len(retrievers) == 0:
            raise ValueError("At least one retriever is required")
        elif len(retrievers) > 1 and agent_model is None:
            raise ValueError("Agent model is required when multiple retrievers are provided")
        elif agent_model is not None:
            am = Creator.create(agent_model.actor.type, agent_model.actor.kwargs)
            self._agent = create_agent(model = am, tools = [retriever.get_tool() for retriever in retrievers])
            self._fallback_agent = create_agent(model = am, tools = [fallback_retriever.get_tool()])
        else:
            self._retrieval_tool = retrievers[0]
            self._fallback_tool = fallback_retriever
            self._retrieval_field, self._fallback_field = self._retrieval_tool.parse_schema_for_query(), self._fallback_tool.parse_schema_for_query()

        self._qr_variables = self._qr_prompt = self._qr_model = None
        if query_refining is not None:
            self._qr_model = Creator.create(query_refining.model.actor.type, query_refining.model.actor.kwargs)
            self._qr_prompt, self._qr_variables = ContextServicePrompt.create(query_refining.prompt.actor)
        self._query_refining_requied = self._qr_prompt is not None and self._qr_model is not None

        self._dg_variables = self._dg_prompt = self._dg_model = None
        self._dg_accept_answers = self._dg_min_threshold_score = None 
        self._dg_max_iterations = None
        if document_grading is not None:
            self._dg_model = Creator.create(document_grading.model.actor.type, document_grading.model.actor.kwargs)
            self._dg_prompt, self._dg_variables = ContextServicePrompt.create(document_grading.prompt.actor)
            self._dg_accept_answers = document_grading.accept_answers
            self._dg_reject_answers = document_grading.reject_answers
            self._dg_min_threshold_score = document_grading.min_threshold_score
            self._dg_max_iterations = document_grading.max_iterations

        self._document_grading_required = self._dg_prompt is not None and self._dg_model is not None

    def __fetch_relevant_documents(self, query: str):
        if self._agent is not None:
            result = self._agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user", 
                            "content": query
                        }
                    ]
                }
            )
            return [Document(page_content=result["messages"][-1].content)] if result is not None and len(result) > 0 else []
        elif self._retrieval_tool is not None:
            result = self._retrieval_tool.get_tool().invoke({self._retrieval_field: query}) if self._retrieval_field is not None else self._retrieval_tool.get_tool().invoke(query)
            results = self._retrieval_tool.parse_result(result=result)
            return [Document(page_content=result) for result in results if len(result) > 0]

    def __grade_document_relevance(self, query: str, document: Document) -> bool:
        messages = self._dg_prompt.format_messages(**{
            self._dg_variables.var_question: query,
            self._dg_variables.var_document: document.page_content
        })
        g_Iteration = 0
        while g_Iteration < 3:
            grading_score = AgenticRetriever.remove_thinkings(self._dg_model.invoke(messages).content)
            result = AgenticRetriever.match_answers(grading_score, self._dg_accept_answers, self._dg_reject_answers)
            if result is not None:
                return result
            RagLogger.logger().info(f"Document grading iteration: {g_Iteration}, invalid grading score for query: {query}")
            g_Iteration += 1

    def refine_query(self, query: str, session_id: str) -> str:
        if not self._query_refining_requied:
            return None, None
        chat_history = "\n\n".join([message.content for message in ConversationHistory.get_messages(session_id)])
        messages = self._qr_prompt.format_messages(**{
            self._qr_variables.var_question: query,
            self._qr_variables.var_history: chat_history
        })
        refined_query = self._qr_model.invoke(messages).content.strip()
        RagLogger.logger().info(f"Refined query from: {query} to: {refined_query}, for session_id: {session_id}")
        return refined_query, chat_history
    
    def _get_relevant_documents(self, query: str, session_id: str):
        documents: list[Document] = []
        chat_history: str = ""
        documents_grading_result = not self._document_grading_required

        cur_iteration = 0
        while True:
            all_documents = self.__fetch_relevant_documents(query)
            if not self._document_grading_required or len(all_documents) == 0:
                documents = all_documents
                break

            if cur_iteration >= self._dg_max_iterations:
                RagLogger.logger().info(f"Document grading reached max iterations: {self._dg_max_iterations} for query: {query}")
                documents = all_documents
                break

            cur_iteration += 1
            relevant_score = 0
            for document in all_documents:
                if self.__grade_document_relevance(query, document):
                    documents.append(document)
                    relevant_score += 1
            RagLogger.logger().info(f"Document grading found {relevant_score} relevant documents out of {len(all_documents)} for query: {query}")
            documents_grading_result = relevant_score / len(all_documents) >= self._dg_min_threshold_score
            if documents_grading_result or not self._query_refining_requied:
                break
            refined_query, chat_history = self.refine_query(query, session_id)
            if refined_query is None:
                break
            query = refined_query

        if not documents_grading_result or len(documents) == 0:
            documents, documents_grading_result = self.__fallback_relevent_documents(query)
        return query, documents, documents_grading_result, chat_history

    def __fallback_relevent_documents(self, query: str):
        results = None
        if self._fallback_agent is not None:
            result = self._fallback_agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user", 
                            "content": query
                        }
                    ]
                }
            )
            results = [result["messages"][-1].content]
        elif self._fallback_tool is not None:
            result = self._fallback_tool.get_tool().invoke({self._fallback_field: query}) if self._fallback_field is not None else self._fallback_tool.get_tool().invoke(query)
            results = self._fallback_tool.parse_result(result)            
        all_documents = [Document(page_content=result) for result in results if len(result) > 0]

        document_grading_result = not self._document_grading_required
        documents = []
        if not self._document_grading_required or len(all_documents) == 0:
            documents = all_documents
        else:    
            relevant_score = 0
            for document in all_documents:
                if self.__grade_document_relevance(query, document):
                    documents.append(document)
                    relevant_score += 1
            RagLogger.logger().info(f"Document grading found {relevant_score} relevant documents out of {len(all_documents)} for query: {query}")
            document_grading_result = relevant_score / len(all_documents) >= self._dg_min_threshold_score
        return documents, document_grading_result
        
    @staticmethod
    def remove_thinkings(response: str) -> str:
        return re.sub(AgenticRetriever.THINKING_RGX, "", response, flags=re.DOTALL|re.IGNORECASE).strip()
    
    @staticmethod
    def match_answers(response: str, accept_answers: list[str], reject_answers: list[str]) -> bool:
        tokens = re.findall(r"\b\w+\b", response.lower())
        if len(tokens) == 1:
            if any([answer.lower() in tokens for answer in accept_answers]):
                return True
            elif any([answer.lower() in tokens for answer in reject_answers]):
                return False
        
        for rgx in AgenticRetriever.ANSWER_RGXs:
            match = re.search(rgx, response, re.IGNORECASE)
            if match:
                result = match.group(1).lower()
                if any([answer.lower() == result for answer in accept_answers]):
                    return True
                elif any([answer.lower() == result for answer in reject_answers]):
                    return False

        tokens = set([tokens[0], tokens[-1]])
        if bool(set([answer.lower() for answer in accept_answers]) & tokens):
            return True
        elif bool(set([answer.lower() for answer in reject_answers]) & tokens):
            return False
        return None

