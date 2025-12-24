This (Agentic) RAG Framework is a configurable Retrieval-Augmented Generation (RAG) system designed to simplify the construction, orchestration, and execution of advanced RAG pipelines. Built on LangChain 1.0.5 (requiring Python 3.10+), the framework provides a structured, extensible foundation for applications that demand accurate, grounded, and high-quality responses powered by external knowledge.

This framework enables developers to build robust RAG workflows using declarative configuration rather than custom code. By integrating retrieval, reasoning, and LLM-based decision-making, the system supports adaptive and agent-like behaviors—known as agentic RAG. This makes question answering more reliable, interpretable, and context-aware.

#### **Key Functionalities**

- **Config-Driven Pipeline Construction** - Build RAG chains declaratively through JSON configuration, enabling reusable and environment-independent setups.
- **Agentic Reasoning Capabilities** - Incorporates LLM-based reasoning steps such as query rewriting, document grading, and answer grounding to improve accuracy and reduce hallucinations.
- **Flexible Retrieval Layer** - Supports multiple vector stores, hybrid retrieval, and custom retrievers
- **Document Grading & Filtering** - Dynamically evaluates retrieved documents for relevance and quality before passing them to the answer synthesis stage.
- **Answer Grounding** - Ensures generated answers are supported by the retrieved evidence, improving factual reliability.
- **Session-Aware Query Understanding** - Optional chat-history reasoning via session-based memory integration.

There are two major phases in typical RAG pipelines - Document Indexing and Answer Generation. The following diagram describes its components and process flow:

![RAG Pipeline](./docs/images/rag-pipeline.png)

For a concise walkthrough of the framework, please follow this [tutorial](./docs/tutorial.md).

### 1. Introduce RAG-Config Template
To construct a RAG pipeline, a JSON-based configuration should be created, specifying the document sources, retrieval behavior, chat models to be used, and the agentic capabilities that govern how the system answers user queries.

A RAG-Config typically consists of the following four sections:
- context_stores: Defines all vector stores used within the RAG pipeline.
- indexing_def: Specifies the indexing process, including loading, splitting, and vectorizing documents, and saving the resulting embeddings to the target vector stores.
- service_def: Describes the available services—such as context-based answer generation and similarity search—along with their required components, including prompts, retrieval methods, chat models (LLMs), and other dependencies.
- logging: Defines the logging behavior.

The following shows the overall JSON-structore of a RAG-Config:
```json
{
    "context_stores": [ ],
    "indexing_def": [ ],
    "service_def": {
        "prompts": [ ],
        "retrievals": [ ],
        "chat_models": [ ],
        "services": [ ],
        "searches": [ ]
    },
    "logging": { }
}
```

### 2. Use Environment Variables
Environment variables can be used in RAG-Configs to define environment-specific settings such as database URLs, access credentials, model names, and other configurable parameters. These variables are typically defined in a separate file and then referenced within the RAG-Config.

The following is an exmple:
```
LLM_INFERENCE="http://127.0.0.1:11434"
LLM_EMBEDDINGS_MODEL="llama3"
```

### 2. Setup Context Stores
The following vector stores and databases are supported for storing indexed document embeddings:
- FAISS
- Chroma
- PgVector
- OpenSearch
- Qdrant
- Weaviate
- Milvus
- PipeCone

For example, the following configuration can be used to set up PgVector:
```json
{
    "name": "vs_pg_vector_customers",
    "actor": {
        "type": "document.store.pgvector.PgVectorVS",
        "kwargs": {
            "embeddings": {
                "type": "langchain_ollama.OllamaEmbeddings",
                "kwargs": {
                    "model":"${LLM_EMBEDDINGS_MODEL}",
                    "base_url": "${LLM_INFERENCE}"
                }
            },
            "connection": "postgresql+psycopg://langchain:langchain@localhost:6024/langchain",
            "collection_name": "customers"
        }
    }
}
```
For instructions on configuring all other vector stores and databases, see [Set up Context Stores](./docs/setup-context-stores.md)

### 3. Index Documents
In a RAG system, documents are indexed first before they can be used as context knowledge for serving requests. This can be achieved by using the following configuration to run indexing services (or combining with other services):

```json
{
    "context_stores": [ ... ]
    "indexing_def": [
        {
            "name": "sales_indexing",
            "loading": {
                "actors": [
                    {
                        "actor": {
                            "type": "document.loading.file.FileLoader",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "file_extensions": ".pdf",
                                "worker": {
                                    "type": "langchain_community.document_loaders.pdf.PyPDFLoader",
                                    "kwargs": {
                                        "extract_images": false
                                    }
                                }
                            }
                        },
                        "scheduler": {
                            "type": "common.scheduling.FileArrivalScheduler",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "recursive": true
                            }        
                        }
                    },                    
                    {
                        "actor": {
                            "type": "document.loading.file.FileLoader",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "recursive": false,
                                "file_extensions": ".txt", 
                                "worker": {
                                    "type": "langchain_community.document_loaders.text.TextLoader",
                                    "kwargs": {
                                        "autodetect_encoding": true
                                    }
                                }
                            }
                        }
                    }
                ],
                "scheduler": {
                    "type": "common.scheduling.CronScheduler",
                    "kwargs": {
                        "crons": ["35 09 * * *"]
                    }
                }
            },
            "splitting": {
                "actor":{
                    "type": "document.splitting.text.TextSplitter",
                    "kwargs": {
                        "worker": {
                            "type": "langchain_text_splitters.character.RecursiveCharacterTextSplitter",
                            "kwargs": { 
                                "chunk_size": 1600,
                                "chunk_overlap": 640
                            }
                        }
                    }
                },
                "concurrency": {
                    "workers": 3
                }
            },
            "indexing": {
                "concurrency": {
                    "workers": 3
                },
                "document_store": "rag_sales"
            }
        },
        { ... }
    ]    
}
```

The indexing process contains 3 steps - loading, splitting and indexing.
#### 3.1 Loading
The loading processs is to load documents from varous source locations. Upon for the formats of source documents, different act loader can be used. For details of various langchain document loaders, please check [here](https://docs.langchain.com/oss/javascript/integrations/providers/all_providers#document-loaders).

- For initial indexing, no schedulers should be configured. The indexing process stops after all documents have been indexed.
- For ongoing incremental indexing, scheduler can be configured for each act loader or at loading level for all act loaders. Schedulers for specific act loaders take higher priority.

Two type of schedulers are supported - cron based time scheduler and file arrival event triggering scheduler.

#### 3.2 Splitting

Once a document is loaded into memory, it goes into the splitting process which breaks the document into chunks. This is done through the configured splitter. Please check [here](https://docs.langchain.com/oss/javascript/integrations/splitters) for details of all langchain text-splitters.

Use the concurrency configuration to spin up additional splitters to relieve back-pressure from the document loading process.

#### 3.3 Indexing
In the indexing process, splitted documents are vectorized by the embedding model configured in the context-store referenced by the document_store element. The resulting vectors are then persisted into the target vectore store.

Same as splitting process, use the concurrency configuration to spin up additional vectorizers to relieve back pressure from the document splitting process.

### 4. Setup a RAG-Chat Application
#### 4.x Enable Agentic Capabilities for the RAG-Chat App
### 6. Run as Services
