Multiple retrievers can be configured for different purposes, such as providing context for LLM generation, performing similarity searches, and other retrieval-based operations.

The following example shows 2 retrievers - one for retrieving documents from a vector-store, the other for web-search.
```json
{
    "retrievals": [
        {
            "name": "it_learning_retrieval",
            "description": "To retrieve IT learning support documents from a local vector store",
            "actor": {
                "type": "qwshen.document.retrieval.vs.VSRetriever",
                "kwargs": {
                    "document_store": "it_learning_vs",
                    "search_type": "similarity",
                    "search_kwargs": {
                        "k": 6,
                        "fetch_k": 32,
                        "score_threshold": 0.8,
                        "lambda_mult": 0.3
                    }
                }
            }
        },
        {
            "name": "it_learning_websearch",
            "description": "To search IT learning information from the Internet",
            "actor": {
                "type": "qwshen.document.retrieval.web.TavilyRetriever",
                "kwargs": {
                    "worker_type":  "langchain_tavily.TavilySearch",
                    "worker_kwargs": {
                        "search_depth": "basic",
                        "max_results": 5
                    }
                }
            }
        }
    ]
}
```

The **document_store** referenced by the vector store retriever must be defined in the context-store section. The pipeline definition validation ensures that this requirement is met.
The web search retriever uses the Tavily search service; therefore, **TAVILY_API_KEY** must be provided in the environment.