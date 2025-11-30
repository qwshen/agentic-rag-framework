from threading import Lock, Thread, Event
import time
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

class ConversationHistory():
    _SESSION_EXPIRATION_SECONDS = 3600    
    lock: Lock = Lock()
    stop_event = Event()
    thread: Thread = None

    conversion_map: dict = {}

    @staticmethod
    def _collect_expired_histories():
        while not ConversationHistory.stop_event.is_set():
            with ConversationHistory.lock:
                now = datetime.now()
                expired_sessions = [
                    session_id for session_id, history in ConversationHistory.conversion_map.items()
                    if (now - history.ts_last_accessed).total_seconds() > ConversationHistory._SESSION_EXPIRATION_SECONDS
                ]
                for session_id in expired_sessions:
                    try:
                        ConversationHistory.conversion_map.pop(session_id)
                    except KeyError:
                        pass
            time.sleep(ConversationHistory._SESSION_EXPIRATION_SECONDS)

    @staticmethod
    def add(session_id: str, messageHistory: BaseChatMessageHistory):
        with ConversationHistory.lock:
            if session_id not in ConversationHistory.conversion_map:
                if ConversationHistory.thread is None or not ConversationHistory.thread.is_alive():
                    ConversationHistory.thread = Thread(target=lambda: (ConversationHistory._collect_expired_histories()), daemon=True)
                    ConversationHistory.thread.start()
                ConversationHistory.conversion_map[session_id] = messageHistory
            return ConversationHistory.conversion_map[session_id]

    @staticmethod
    def get_messages(session_id: str):
        with ConversationHistory.lock:
            cm_history = ConversationHistory.conversion_map.get(session_id, None)
            return cm_history.messages if cm_history is not None else []
        
class BufferWindowConversionHistory(BaseChatMessageHistory, BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    k: int = Field(default=8)
    ts_last_accessed: datetime = Field(default_factory=datetime.now)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        self.messages.extend(messages)
        self.messages = self.messages[-self.k:]
        self.ts_last_accessed =  datetime.now()

    def clear(self) -> None:
        self.messages.clear()

    @staticmethod
    def get_chat_history(session_id: str, k: int = 4):
        return ConversationHistory.add(session_id=session_id, messageHistory=BufferWindowConversionHistory(k=k))
    
    @staticmethod
    def create_chain_with_history(rag_chain, var_input: str, var_history: str, k: int=4):
        return RunnableWithMessageHistory(
            rag_chain,
            get_session_history=lambda session_id: BufferWindowConversionHistory.get_chat_history(session_id, k=k),
            input_messages_key=var_input,
            history_messages_key=var_history,
            history_factory_config=[
                ConfigurableFieldSpec(id="session_id", annotation=str, default="id_default", name="Session Id", description="The session ID to use for the chat history")
            ]
        )        

class BufferWindowConversationSummaryHistory(BaseChatMessageHistory, BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    k: int = Field(default=8)
    m: BaseChatModel = Field(default_factory=BaseChatModel)
    ts_last_accessed: datetime = Field(default_factory=datetime.now)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        existing_summary = self.messages.pop(0).content if len(self.messages) > 0 else None
        self.messages.extend(messages)
        self.messages = self.messages[-self.k:]

        summary_messages = None
        conversation_messages = "\n\n".join(f"User: {message.content}" if isinstance(message, HumanMessage) else f"AI: {message.content}" for message in self.messages)
        if existing_summary is None:
            summary_prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Given the following conversations, generate a summary. Ensuring to maintain as much relevant information as possible."
                ),
                HumanMessagePromptTemplate.from_template(
                    "Conversions:\n{conversation_messages}"
                )
            ])
            summary_messages = summary_prompt.format_messages(**{"conversation_messages": conversation_messages})
        else:
            summary_prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Given the existing conversation summary and all following conversations, generate a new summary. Ensuring to maintain as much relevant information as possible."
                ),
                HumanMessagePromptTemplate.from_template(
                    "Existing Summary:\n{existing_summary}\n\nConversions:\n{conversation_messages}"
                )
            ])
            summary_messages = summary_prompt.format_messages(**{"existing_summary": existing_summary, "conversation_messages": conversation_messages})
        new_summary = self.m.invoke(summary_messages)
        self.messages.insert(0, SystemMessage(content=new_summary.content))
        self.ts_last_accessed =  datetime.now()

    def clear(self) -> None:
        self.messages.clear()

    @staticmethod
    def get_chat_history(session_id: str, m: BaseChatModel, k: int = 4):
        return ConversationHistory.add(session_id=session_id, messageHistory=BufferWindowConversationSummaryHistory(m=m, k=k))

    @staticmethod
    def create_chain_with_history(rag_chain, var_input: str, var_history: str, m: BaseChatModel, k: int=4):
        return RunnableWithMessageHistory(
            rag_chain,
            get_session_history=lambda session_id: BufferWindowConversationSummaryHistory.get_chat_history(session_id, m=m, k=k),
            input_messages_key=var_input,
            history_messages_key=var_history,
            history_factory_config=[
                ConfigurableFieldSpec(id="session_id", annotation=str, default="id_default", name="Session Id", description="The session ID to use for the chat history")
            ]
        )
