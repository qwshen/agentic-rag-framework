import os
from typing import Iterator
from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from sse_starlette import EventSourceResponse
import json
from functools import reduce

from qwshen.common.logging import RagLogger
from qwshen.service.service import ServiceOperator
from qwshen.launcher import Launcher

CTX_API_VERSION: str = "1.0.0"
CTX_API_TOKEN: str = "ctx-api-token"
CTX_API_PORT: str = "CTX_API_PORT"

CTX_COMPLETION_PATH: str = "CTX_COMPLETION_PATH"
CTX_SEARCH_PATH: str = "CTX_SEARCH_PATH"

#
# The ContextAPI class responds user-queries for text generation and similarity search. The chat/search methods will return an iterator of string, which will be used for streaming response back to user.
class ContextAPI(FastAPI):
    def __init__(self, title: str, version: str, description: str):
        super().__init__(title=title, version=version, description=description)

        api_token, services = ContextAPI._init_setup()
        self._api_token = api_token
        self._context_services = [service for service in services if ServiceOperator.is_context_service(service[0])]
        self._search_services = [service for service in services if ServiceOperator.is_search_service(service[0])]

    def completion(self, session_id: str, play_load: dict) -> Iterator[str]:
        try:
            user_query, service_name = self._verify(play_load)

            context_service = None
            if service_name is not None:
                context_service = [service for service, _ in self._context_services if service.get_name() == service_name][0]
            elif len(self._context_services) > 0:
                context_service, _ = self._context_services[0]
            if context_service is None:
                raise HTTPException(501, f"{service_name} does not exist or is not a context-service")
            
            RagLogger.logger().debug(f"user-query for completion [{service_name}] received: {user_query}")
            for message in context_service.process(user_query, kwargs={"session_id": session_id}):
                yield message.content if message is not None else ""
            RagLogger.logger().info(f"user-query for completion [{service_name}] done: {user_query}")
        except Exception as e:
            RagLogger.logger().error(str(e))
            raise HTTPException(500, "Server internal error")

    def search(self, play_load: dict) -> Iterator[str]:
        try:
            user_query, service_name = self._verify(play_load)

            search_service = None
            if service_name is not None:
                search_service = [service for service, _ in self._search_services if service.get_name() == service_name][0]
            elif len(self._search_services) > 0:
                search_service, _ = self._search_services[0]
            if search_service is None:
                raise HTTPException(501, f"{service_name} does not exist or is not a search-service")
            
            RagLogger.logger().debug(f"user-query for search [{service_name}] received: {user_query}")
            for message in search_service.process(user_query, play_load.get("search_kwargs", {})):
                yield message.content if message is not None else ""
            RagLogger.logger().debug(f"user-query for search [{service_name}] done: {user_query}")
        except Exception as e:
            RagLogger.logger().error(str(e))
            raise HTTPException(500, "Server error")

    def authenticate(self, req: Request):
        api_token = req.headers.get(CTX_API_TOKEN, None)
        if api_token is None or api_token != self._api_token:
            raise HTTPException(401, "No api-token provided")
        return req.query_params.get("sid", None)
    
    def _verify(self, play_load: dict) -> tuple[str, str]:
        user_query: str = play_load.get("user_query", None)
        if user_query is None or len(user_query) <= 0:
            raise HTTPException(401, "No user-query provided")
        return (user_query, play_load.get("service_name", None))
    
    @staticmethod
    def _init_setup():
        indexers, services = Launcher.start()
        if reduce(lambda x, y: x or y, [indexer.index_scheduled() for indexer in indexers], False):
            RagLogger.logger.info("Indexing scheduled.")

        api_token: str =  os.environ.get(CTX_API_TOKEN.upper().replace("-", "_"), None)
        if api_token is None or len(api_token) <= 0:
            msg = f"Server error - {CTX_API_TOKEN.upper()} is missing in environment"
            RagLogger.logger.error(msg)
            raise HTTPException(501, msg)
        
        return api_token, services

    @staticmethod
    def getApiPort():
        return int(os.environ.get(CTX_API_PORT, "8000"))
    @staticmethod
    def getCompletionPath():
        return os.environ.get(CTX_COMPLETION_PATH, "/completion")
    @staticmethod
    def getSearchPath():
        return os.environ.get(CTX_SEARCH_PATH, "/search")

# create context-api object
ctxApi = ContextAPI(title="Context API Service", version=CTX_API_VERSION, description="Context API service for chat-completion/similarity-search")

@ctxApi.post(ContextAPI.getCompletionPath())
async def completion(request: Request):
    session_id = ctxApi.authenticate(request)
    return EventSourceResponse(ctxApi.completion(session_id, await request.json()), media_type="text/plain")

@ctxApi.post(ContextAPI.getSearchPath())
async def search(request: Request):
    ctxApi.authenticate(request)
    return EventSourceResponse(ctxApi.search(await request.json()), media_type="text/plain")

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
