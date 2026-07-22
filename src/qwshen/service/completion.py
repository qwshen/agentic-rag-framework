from typing import Iterator

from langchain_core.messages.ai import AIMessage  
from langchain_core.runnables import RunnableSequence
from langchain_core.runnables.history import RunnableWithMessageHistory

from qwshen.common.component import Creator
from qwshen.common.logging import RagLogger
from .types import ServiceRethinkingAgent, ServiceReasoningAgent, PromptVariables, ContextServicePrompt, ServiceRunner
from .retrieval import AgenticRetriever

class AgenticCompletion:
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
            self._ag_reject_answers = answer_grounding.reject_answers
            self._ag_max_iterations = answer_grounding.max_iterations
        self._answer_grounding_required = self._ag_prompt is not None and self._ag_model is not None

        self._ar_prompt = self._ar_variables = None
        self._ar_model = None
        if answer_rewriting is not None:
            self._ar_model = Creator.create(answer_rewriting.model.actor.type, answer_rewriting.model.actor.kwargs)
            self._ar_prompt, self._ar_variables = ContextServicePrompt.create(answer_rewriting.prompt.actor)
        self._answer_rewriting_required = self._ar_prompt is not None and self._ar_model is not None

    def invoke(self, user_query: str, session_id: str, kwargs: dict) -> Iterator[AIMessage]:        
        documents_grading_result = None
        cur_answer: AIMessage = None
        answer_grounding_result = None

        cur_iteration = 0
        documents = chat_history = None
        while True:
            user_query, documents, documents_grading_result, chat_history = self._document_retriever._get_relevant_documents(user_query, session_id)

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
                self._ag_variables.var_answer: AgenticRetriever.remove_thinkings(cur_answer.content)
            }
            if self._ag_variables.var_context is not None:
                inputs[self._ag_variables.var_context] = "\n\n".join([document.page_content for document in documents])
            elif self._ag_variables.var_document is not None:
                inputs[self._ag_variables.var_document] = "\n\n".join([document.page_content for document in documents])
            if self._ag_variables.var_history is not None:
                inputs[self._ag_variables.var_history] = chat_history

            grounding_score = AgenticRetriever.remove_thinkings(self._ag_model.invoke(self._ag_prompt.format_messages(**inputs)).content)
            answer_grounding_result = AgenticRetriever.match_answers(grounding_score, self._ag_accept_answers, self._ag_reject_answers)
            RagLogger.logger().info(f"Answer grounding score: {grounding_score}, for query: {user_query}")
            if answer_grounding_result:
                break

            cur_iteration += 1
            if cur_iteration >= self._ag_max_iterations:
                RagLogger.logger().info(f"Answer grounding reached max iterations: {self._ag_max_iterations} for query: {user_query}")
                break
            refined_query, _ = self._document_retriever.refine_query(user_query, session_id)
            if refined_query is None:
                break
            RagLogger.logger().info(f"Refined query for answer grounding from: {user_query} to: {refined_query}, for session_id: {session_id}")
            user_query = refined_query

        auto_answer_rewriting = True if documents_grading_result and (answer_grounding_result is None or not answer_grounding_result) else False
        if self._answer_rewriting_required and cur_answer is not None and auto_answer_rewriting:
            inputs = {
                self._ar_variables.var_answer: AgenticRetriever.remove_thinkings(cur_answer.content)
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
            RagLogger.logger().info(f"Answer rewritten for query: {user_query}, for session_id: {session_id}")
        yield cur_answer
