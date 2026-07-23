import os
from typing import Iterator
from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from sse_starlette import EventSourceResponse
from functools import reduce
from langchain_core.messages.human import HumanMessage

from qwshen.common.logging import RagLogger
from qwshen.common.chat_history import ConversationHistory
from qwshen.service.service import ServiceOperator
from qwshen.launcher import Launcher

CTX_API_VERSION: str = "1.0.0"
CTX_API_TOKEN: str = "ctx-api-token"
CTX_API_PORT: str = "CTX_API_PORT"

CTX_COMPLETION_PATH: str = "CTX_COMPLETION_PATH"
CTX_SEARCH_PATH: str = "CTX_SEARCH_PATH"
CTX_HISTORY_PATH: str = "CTX_HISTORY_PATH"

#
# The ContextAPI class responds user-queries for text generation and similarity search. The chat/search methods will return an iterator of string, which will be used for streaming response back to user.
class ContextAPI(FastAPI):
    def __init__(self, title: str, version: str, description: str):
        super().__init__(title=title, version=version, description=description)

        tokenServices = ContextAPI._init_setup()
        self._context_services = {}
        self._search_services = {}
        tokens = []
        for token, service in tokenServices:
            if ServiceOperator.is_context_service(service):
                self._context_services[token] = service
            elif ServiceOperator.is_search_service(service):
                self._search_services[token] = service
            tokens.append(token)
        self._api_tokens = set(tokens)

    def completion(self, api_token: str, session_id: str, pay_load: dict) -> Iterator[str]:
        try:
            user_query, _, _ = self._verify(pay_load)
            context_service = self._context_services.get(api_token, None)
            if context_service is None:
                RagLogger.logger().error(f"Context-Service not authroized - {session_id}")
                raise HTTPException(401, f"Context-Service not authroized - {session_id}")
            
            RagLogger.logger().debug(f"user-query for completion [{context_service.get_name()}] received: {user_query} from {session_id}")
            for message in context_service.process(user_query, kwargs={"session_id": session_id}):
                yield message.content if message is not None else ""
            RagLogger.logger().info(f"user-query for completion [{context_service.get_name()}] done: {user_query}")
        except Exception as e:
            RagLogger.logger().error(str(e))
            raise HTTPException(500, "Server internal error")

    def search(self, api_token: str, pay_load: dict) -> Iterator[str]:
        try:
            user_query, search_kwargs, output_column = self._verify(pay_load)

            search_service = self._search_services.get(api_token, None)
            if search_service is None:
                RagLogger.logger().error(f"Search service not authroized")
                raise HTTPException(401, f"Search service not authorized")
            
            RagLogger.logger().debug(f"user-query for search [{search_service.get_name()}] received: {user_query}")
            for message in search_service.process(user_query, search_kwargs):
                yield (message.metadata.get(output_column, "") if output_column is not None else message.page_content) if message is not None else ""
            RagLogger.logger().debug(f"user-query for search [{search_service.get_name()}] done: {user_query}")
        except Exception as e:
            RagLogger.logger().error(str(e))
            raise HTTPException(500, "Server error")

    def history(self, api_token: str, session_id: str) -> Iterator[str]:
        try:
            context_service = self._context_services.get(api_token, None)
            if context_service is None:
                RagLogger.logger().error(f"Context-Service not authroized - {session_id}")
                raise HTTPException(401, f"Context-Service not authroized - {session_id}")

            context_service.launch_chat_history(session_id)

            RagLogger.logger().debug(f"fetching conversation history for {session_id}")
            for message in ConversationHistory.get_messages(session_id=session_id):
                yield "^~@^HM" if isinstance(message, HumanMessage) else "^~@^AM"
                yield message.content
            RagLogger.logger().debug(f"fetching conversation history for {session_id} done")    
        except Exception as e:
            RagLogger.logger().error(str(e))
            raise HTTPException(500, "Server error")

    def authenticate(self, req: Request):
        api_token = req.headers.get(CTX_API_TOKEN, None)
        if api_token is None or api_token not in self._api_tokens:
            RagLogger.logger().error(f"No api-token provided or api-token invalid")
            raise HTTPException(401, "No api-token provided")
        return (api_token, req.query_params.get("sid", None))
    
    def _verify(self, pay_load: dict) -> tuple[str, str]:
        user_query: str = pay_load.get("user_query", None)
        if user_query is None or len(user_query) <= 0:
            RagLogger.logger().error("No user-query provided")
            raise HTTPException(401, "No user-query provided")
        return user_query, pay_load.get("search_kwargs", {}), pay_load.get("output_column", None)
    
    @staticmethod
    def _init_setup():
        indexers, services = Launcher.start()
        if reduce(lambda x, y: x or y, [indexer.index_scheduled() for indexer in indexers], False):
            RagLogger.logger().info("Indexing scheduled.")

        tokenServices = []
        for service in services:
            for token in service[1]:
                tokenServices.append((token, service[0]))
        return tokenServices

    @staticmethod
    def getApiPort():
        return int(os.environ.get(CTX_API_PORT, "8000"))
    @staticmethod
    def getCompletionPath():
        return os.environ.get(CTX_COMPLETION_PATH, "/completion")
    @staticmethod
    def getSearchPath():
        return os.environ.get(CTX_SEARCH_PATH, "/search")
    @staticmethod
    def getHistoryPath():
        return os.environ.get("CTX_HISTORY_PATH", "/history")

# create context-api object
ctxApi = ContextAPI(title="Context API Service", version=CTX_API_VERSION, description="Context API service for chat-completion/similarity-search")

@ctxApi.post(ContextAPI.getCompletionPath())
async def completion(request: Request):
    api_token, session_id = ctxApi.authenticate(request)
    if api_token not in ctxApi._context_services:
        raise HTTPException(401, "Context service not authroized")
    return EventSourceResponse(ctxApi.completion(api_token, session_id, await request.json()), media_type="text/event-stream")

@ctxApi.post(ContextAPI.getSearchPath())
async def search(request: Request):
    api_token, _ = ctxApi.authenticate(request)
    if api_token not in ctxApi._search_services:
        raise HTTPException(401, "Search service not authroized")
    return EventSourceResponse(ctxApi.search(api_token, await request.json()), media_type="text/event-stream")

@ctxApi.get(ContextAPI.getHistoryPath())
async def history(request: Request):
    api_token, session_id = ctxApi.authenticate(request)
    if api_token not in ctxApi._context_services:
        raise HTTPException(401, "Context service not authroized")
    return EventSourceResponse(ctxApi.history(api_token, session_id), media_type="text/event-stream")

if __name__ == "__main__":
    ssl_cert = os.environ.get("RAG_API_SSL_CERT", None)
    ssl_key = os.environ.get("RAG_API_SSL_KEY", None)

    import uvicorn
    if ssl_cert is not None and ssl_key is not None:
        RagLogger.logger().info("ContextAPI is running with TLS")
        ssl_key_pwd = os.environ.get("RAG_API_SSL_KEY_PWD", None)
        if ssl_key_pwd is None:
            uvicorn.run(ctxApi, host="0.0.0.0", port=ContextAPI.getApiPort(), ssl_certfile=ssl_cert, ssl_keyfile=ssl_key) 
        else:
            uvicorn.run(ctxApi, host="0.0.0.0", port=ContextAPI.getApiPort(), ssl_certfile=ssl_cert, ssl_keyfile=ssl_key, ssl_keyfile_password=ssl_key_pwd) 
    else:
        RagLogger.logger().info("Cert is not provided. ContextAPI is running without TLS")
        uvicorn.run(ctxApi, host="0.0.0.0", port=ContextAPI.getApiPort()) 
