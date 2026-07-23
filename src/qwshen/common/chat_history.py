from threading import Lock, Thread, Event
import time
from datetime import datetime
import psycopg
from abc import ABC, abstractmethod

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_postgres import PostgresChatMessageHistory

class ConversationHistoryBase(ABC):
    def __init__(self, in_memory: bool):
        self.in_memory = in_memory
        self.ts_last_accessed = datetime.now

    @abstractmethod 
    def get_messages(self): list[BaseMessage]

class ConversationHistory():
    _TABLE_NAME = "chat_history"
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
                    if history.in_memory and ((now - history.ts_last_accessed).total_seconds() > ConversationHistory._SESSION_EXPIRATION_SECONDS)
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
    def exist(session_id: str):
        return ConversationHistory.conversion_map[session_id] if session_id in ConversationHistory.conversion_map else None
    
    @staticmethod
    def get_messages(session_id: str):
        with ConversationHistory.lock:
            cm_history = ConversationHistory.conversion_map.get(session_id, None)
            return cm_history.get_messages() if cm_history is not None else []


class BufferWindowConversionHistory(BaseChatMessageHistory, ConversationHistoryBase):
    def __init__(self, k):
        ConversationHistoryBase.__init__(self, in_memory=True)
        self.k = k
        self.messages = []

    def add_messages(self, messages: list[BaseMessage]) -> None:
        self.messages.extend(messages)
        self.messages = self.messages[-self.k:]
        self.ts_last_accessed =  datetime.now()

    def get_messages(self) -> list[BaseMessage]:
        return self.messages
    
    def clear(self) -> None:
        self.messages.clear()

    @staticmethod
    def get_chat_history(session_id: str, k: int = 4):
        messageHistory = ConversationHistory.exist(session_id)        
        return ConversationHistory.add(session_id=session_id, messageHistory=BufferWindowConversionHistory(k=k)) if messageHistory is None else messageHistory
    
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

class BufferWindowConversationSummaryHistory(BaseChatMessageHistory, ConversationHistoryBase):
    def __init__(self, k: int, m: BaseChatModel):
        ConversationHistoryBase.__init__(self, in_memory=True)
        self.k = k
        self.m = m
        self.messages = []

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

    def get_messages(self) -> list[BaseMessage]:
        return self.messages

    def clear(self) -> None:
        self.messages.clear()

    @staticmethod
    def get_chat_history(session_id: str, m: BaseChatModel, k: int = 4):
        messageHistory = ConversationHistory.exist(session_id)        
        return ConversationHistory.add(session_id=session_id, messageHistory=BufferWindowConversationSummaryHistory(m=m, k=k)) if messageHistory is None else messageHistory

    @staticmethod
    def create_chain_with_history(rag_chain, var_input: str, var_history: str, model: BaseChatModel, k: int=4):
        return RunnableWithMessageHistory(
            rag_chain,
            get_session_history=lambda session_id: BufferWindowConversationSummaryHistory.get_chat_history(session_id, m=model, k=k),
            input_messages_key=var_input,
            history_messages_key=var_history,
            history_factory_config=[
                ConfigurableFieldSpec(id="session_id", annotation=str, default="id_default", name="Session Id", description="The session ID to use for the chat history")
            ]
        )


class PostgresWindowConversationHistory(BaseChatMessageHistory, ConversationHistoryBase):
    def __init__(self, session_id, db_url: str, k=8):
        ConversationHistoryBase.__init__(self, in_memory=False)

        sync_conn = psycopg.connect(db_url)
        PostgresChatMessageHistory.create_tables(sync_conn, ConversationHistory._TABLE_NAME)
        self.history = PostgresChatMessageHistory(ConversationHistory._TABLE_NAME, session_id, sync_connection=sync_conn)

        self.k = k

    @property
    def messages(self) -> list[BaseMessage]:
        return self.history.messages[-self.k:]

    def add_messages(self, messages):
        self.history.add_messages(messages)
        self.ts_last_accessed =  datetime.now()

    def get_messages(self) -> list[BaseMessage]:
        return self.history.messages[-self.k:]

    def clear(self):
        self.history.clear()

    @staticmethod
    def get_chat_history(session_id: str, db_url: str, k: int=4):
        messageHistory = ConversationHistory.exist(session_id)        
        return ConversationHistory.add(session_id=session_id, messageHistory=PostgresWindowConversationHistory(session_id=session_id,db_url=db_url, k=k)) if messageHistory is None else messageHistory

    @staticmethod
    def create_chain_with_history(rag_chain, db_url: str, var_input: str, var_history: str, k: int=4):
        return RunnableWithMessageHistory(
            rag_chain,
            get_session_history=lambda session_id: PostgresWindowConversationHistory.get_chat_history(session_id, db_url=db_url, k=k),
            input_messages_key=var_input,
            history_messages_key=var_history,
            history_factory_config=[
                ConfigurableFieldSpec(id="session_id", annotation=str, name="Session Id", description="Conversation identifier")
            ]
        )        


class PostgresWindowConversationSummaryHistory(BaseChatMessageHistory, ConversationHistoryBase):
    def __init__(self, session_id, db_url: str, model: BaseChatModel, k=8):
        ConversationHistoryBase.__init__(self, in_memory=False)

        sync_conn = psycopg.connect(db_url)
        PostgresChatMessageHistory.create_tables(sync_conn, ConversationHistory._TABLE_NAME)
        self.history = PostgresChatMessageHistory("chat_history", session_id, sync_connection=sync_conn)

        self.k = k
        self.m = model

    @property
    def messages(self) -> list[BaseMessage]:
        return self.history.messages[-self.k:]

    def add_messages(self, messages: list[BaseMessage]) -> None:
        existing_summary = self.history.pop(0).content if len(self.messages) > 0 else None
        self.history.extend(messages)
        self.history = self.history[-self.k:]

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
        self.history.insert(0, SystemMessage(content=new_summary.content))
        self.ts_last_accessed =  datetime.now()

    def get_messages(self) -> list[BaseMessage]:
        return self.history.messages[-self.k:]

    def clear(self) -> None:
        self.history.clear()

    @staticmethod
    def get_chat_history(session_id: str, db_url: str, model: BaseChatModel, k: int = 4):
        messageHistory = ConversationHistory.exist(session_id)        
        return ConversationHistory.add(session_id=session_id, messageHistory=PostgresWindowConversationSummaryHistory(session_id=session_id, db_url=db_url, model=model, k=k)) if messageHistory is None else messageHistory

    @staticmethod
    def create_chain_with_history(rag_chain, db_url: str, model: BaseChatModel, var_input: str, var_history: str, k: int=4):
        return RunnableWithMessageHistory(
            rag_chain,
            get_session_history=lambda session_id: PostgresWindowConversationSummaryHistory.get_chat_history(session_id, db_url=db_url, model=model, k=k),
            input_messages_key=var_input,
            history_messages_key=var_history,
            history_factory_config=[
                ConfigurableFieldSpec(id="session_id", annotation=str, name="Session Id", description="Conversation identifier")
            ]
        )        
