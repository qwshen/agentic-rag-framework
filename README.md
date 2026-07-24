This (Agentic) RAG Framework is a configurable Retrieval-Augmented Generation (RAG) system designed to simplify the construction, orchestration, and execution of advanced RAG pipelines. Built on LangChain 1.0.5 (requiring Python 3.10+), the framework provides a structured, extensible foundation for applications that demand accurate, grounded, and high-quality responses powered by custom knowledge.

This framework enables developers to build robust RAG workflows using declarative configuration rather than custom code. By integrating retrieval, reasoning, and LLM-based decision-making, the system supports adaptive and agent-like behaviors—known as agentic RAG. This makes question answering more reliable, interpretable, and context-aware.

#### **Key Functionalities**

- **Config-Driven Pipeline Construction** - Build RAG chains declaratively through JSON configuration, enabling reusable and environment-independent setups.
- **Agentic Reasoning Capabilities** - Incorporates LLM-based reasoning steps such as query rewriting, document grading, and answer grounding to improve accuracy and reduce hallucinations.
- **Flexible Retrieval Layer** - Supports multiple vector stores, hybrid retrieval, and custom retrievers
- **Document Grading & Filtering** - Dynamically evaluates retrieved documents for relevance and quality before passing them to the answer synthesis stage.
- **Answer Grounding** - Ensures generated answers are supported by the retrieved evidence, improving factual reliability.
- **Session-Aware Query Understanding** - Optional chat-history reasoning via session-based integration.

For featuer changes, please refer to the [Change Logs](./docs/change-logs.md)

There are two major phases in typical RAG pipelines - Document Indexing and Answer Generation. The following diagram describes its components and process flow:

![RAG Pipeline](./docs/images/rag-pipeline.png)


### 0. Set up project
- Install Python 3.10+ and set up a virutla environment
- Install required packages
  ```shell
  pip install -r ./requirements.txt
  ```
- Set up the project
  ```shell
  pip install . -e
  ```
  
For a concise walkthrough of the framework, please follow this [tutorial](./tutorial/README.md).


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


### 3. Setup Context Stores
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
    "context_stores": [
        {
            "name": "vs_pg_vector_customers",
            "actor": {
                "type": "qwshen.document.store.pgvector.PgVectorVS",
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
        },
        ...
    ]
}
```
For instructions on configuring all other vector stores and databases, see [Set up Context Stores](./docs/setup-context-stores.md)


### 4. Index Documents
In a RAG system, documents are indexed first before they can be used as context knowledge for serving requests. This can be achieved by using the following configuration to run indexing services (or combining with other services):

```json
{
    "context_stores": [ ... ],
    "indexing_def": [
        {
            "name": "sales_indexing",
            "loading": {
                "actors": [
                    {
                        "actor": {
                            "type": "qwshen.document.loading.file.FileLoader",
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
                            "type": "qwshen.common.scheduling.FileArrivalScheduler",
                            "kwargs": {
                                "directory": "${DOCUMENTS_DIRECTORY}/sales",
                                "recursive": true
                            }        
                        }
                    },                    
                    {
                        "actor": {
                            "type": "qwshen.document.loading.file.FileLoader",
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
                    "type": "qwshen.common.scheduling.CronScheduler",
                    "kwargs": {
                        "crons": ["35 09 * * *"]
                    }
                }
            },
            "splitting": {
                "actors": [
                    {
                        "type": "qwshen.document.splitting.text.TextSplitter",
                        "kwargs": {
                            "worker": {
                                "type": "langchain_text_splitters.character.RecursiveCharacterTextSplitter",
                                "kwargs": { 
                                    "chunk_size": 1600,
                                    "chunk_overlap": 640
                                }
                            }
                        },
                        "chunk_size_threshold": 320,
                        "chunk_size_strategy": "discard"
                    }
                ],
                "chunk_size_threshold": 1024,
                "chunk_size_strategy": "append"
            },
            "indexing": {
                "document_size_threshold": 160,
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

In the configuration, an indexing process consists of three steps: loading, splitting, and indexing. Multiple indexing processes can be defined, each handling different document formats from different sources and persisting the results to separate vector stores.


#### 4.1 Loading
The loading step is to load documents from varous source locations. Upon for the formats of source documents, different act loader can be used. For instructions on configuring all document loaders, see [Set up Loaders](./docs/setup-loaders.md)

- For initial indexing, no schedulers should be configured. The indexing process stops after all documents have been indexed.
- For ongoing incremental indexing, scheduler can be configured for each act loader or at loading level for all act loaders. Schedulers for specific act loaders take higher priority.

Two type of schedulers are supported - cron based time scheduler and file arrival event triggering scheduler.


#### 4.2 Splitting

Once a document is loaded into memory, it goes into the splitting step which breaks the document into chunks. This is done through the configured splitters.

During the splitting process, small documents may be either combined or discarded depending on the *chunk_size_threshold* and the selected *chunk_size_strategy* (either append or discard). The *chunk_size_threshold* and *chunk_size_strategy* can be configured for each act splitter or at splitting level for all act splitter. The *chunk_size_threshold* and *chunk_size_strategy* for specific act splitters take higher priority.

For instructions on configuring all document splitters, see [Set up Splitting](./docs/setup-splitters.md)


#### 4.3 Indexing
In the indexing step, splitted documents are vectorized by the embedding model configured in the context-store referenced by the *document_store* element. The resulting vectors are then persisted into the target vectore store.

```json
{
    "indexing": {
        "document_store": "it_learning",
        "concurrency": {
            "workers": 3
        },
        "document_size_threshold": 320
    }
}
```

The *document_size_threshold* determines the size limit for documents to be persisted.

Use the **concurrency** configuration to spin up additional vectorizers to relieve back pressure from the document splitting step.


### 5. Construct a RAG-Chat Application
A simple RAG application can be defined with the following configuration:
```json
"service_def": {
    "context_stores": [ ... ],
    "prompts": [
        {
            "name": "chat_prompt",
            "actor": {
                "type": "qwshen.common.prompt.load_from_file",
                "kwargs": {
                    "path": "${CHAT_PROMPT_FILE}"
                }
            }                
        }
    ],
    "chat_models": [
        {
            "name": "mistral:7b",
            "actor": {
                "type": "langchain_ollama.ChatOllama",
                "kwargs": {
                    "base_url": "${LLM_INFERENCE}",
                    "model": "mistral:7b",
                    "temperature": 0.0
                }
            }
        }
    ],
    "retrievals": [
        {
            "name": "r_customers",
            "description": "Customer support documents",
            "search": {
                "type": "similarity",
                "kwargs": {
                    "k": 6,
                    "fetch_k": 16,
                    "score_threshold": 0.8,
                    "filter": {
                        "paper_title": "GPT-4 Technical Report"
                    },
                    "lambda_mult": 0.3
                },
                "document_store": "vs_pg_vector_customers"
            }
        }
    ],
    "services": [
        {
            "name": "customer_support_chat",
            "definition": {
                "prompt": {
                    "ref": "chat_prompt"
                },
                "context": {
                    "ref_retrievals": ["r_customers"]
                },
                "generation": {
                    "ref_model": "deepseek-r1:1.5b"
                }
            },
            "access_roles": [
                "api-test-token-08312"
            ]
        }
    ]
}
```
At a minimum, a RAG application requires a prompt, a context store, and an LLM. A user question is incorporated into the prompt, which is then augmented with documents retrieved from the context store. Using this contextual knowledge, the LLM generates a response to the user’s question.

- For configuring prompts, please refer to [here](./docs/setup-prompts.md)
- For configuring LLM models, please refer to [here](./docs/setup-llm-models.md)
- For configuring retrievals, please refer [here](./docs/setup-retrievals.md)

#### 5.1 Inject user's chat history in the service definition
Please use the following configuration to inject a user’s chat history, allowing the LLM to understand the conversational context.
```json
"prompt": {
    "ref": "chat_prompt",
    "with_history": {
        "storage": "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}",
        "use_summary": false,
        "window_k": 5
    }
}
```
- **storage**: defines where the conversation history is stored. It must be either "memory" (the default when not specified) or a valid PostgreSQL connection string. If a PostgreSQL connection string is provided, the conversation history is persisted in the chat_history table.
- **user_summary**: when set to true, a summary of the user’s chat history is generated and used; otherwise, the raw messages are used.
- **window_k**: the number of messages.

#### 5.2 Enable retrieval agent
When there are more than one retrievals being used, the model for creating an retrieval agent is required. The following shows one example:
```json
"context": {
    "ref_retrievals": ["r_customers", "r_sales"],
    "agent": {
        "ref_model": "gpt-oss:20b"
    },
    "fallback_retrieval": "it_learning_websearch"
}
```
- If only one retrieval is defined in **ref_retrievals**, the agent model can be omitted.
- If no documents are retrieved from any of the configured retrievers, **fallback_retrieval** is invoked. However, **fallback_retrieval** is optional.

#### 5.3 Enable agentic capabilities
Agentic capabilities refer to the system’s ability to act autonomously or semi-autonomously to achieve specific tasks, rather than just passively responding to user queries. This can be achieved by adding the following configuration in the difinition of a service:
```json
"generation": {
    "ref_model": "deepseek-r1:1.5b",
    "answer_rewriting": {
        "ref_prompt": "answer_rewriting_prompt",
        "ref_model": "llama3.2"
    }
},
"agentivity": {
    "query_refining": {
        "ref_prompt": "query_refining_prompt",
        "ref_model": "llama3.2"
    },
    "document_grading": {
        "ref_prompt": "document_grading_prompt",
        "ref_model": "deepseek-r1:1.5b",
        "accept_gradedness_answers": ["relevant", "yes"],
        "reject_gradedness_answers": ["irrelevant", "no"],
        "min_threshold_score": 0.6,
        "max_iterations": 2
    },
    "answer_grounding": {
        "ref_prompt": "answer_grounding_prompt",
        "ref_model": "deepseek-r1:1.5b",
        "accept_groundedness_answers": ["yes"],
        "reject_groundedness_answers": ["no"],
        "max_iterations": 3
    }
}
```
This requires several additional prompts containing clear, specific instructions, allowing the LLM to generate responses as intended that serve as the outputs of re-thinking or reasoning. Note that each of **answer_rewriting**, **query_refining**, **document_grading** and **answer_grounding** can be defined independently. For example, only document-grading may be provided.
```json
"generation": {
    "ref_model": "deepseek-r1:1.5b"
},
"agentivity": {
    "document_grading": {
        "ref_prompt": "document_grading_prompt",
        "ref_model": "deepseek-r1:1.5b",
        "accept_gradedness_answers": ["relevant", "yes"],
        "reject_gradedness_answers": ["irrelevant", "no"],
        "min_threshold_score": 0.6,
        "max_iterations": 2
    }
}
```

Please refer to [Configure Agentivity](./docs/setup-agentivity.md) for more details on configuring different agentic behaviors.

#### 5.4 Combine document-grading and fallback-retrieval
When both **document_grading** and **fallback_retrieval** are configured, **fallback_retrieval** is invoked when the overal document relevance-score does not meet the threshold defined in **document_grading**.

#### 5.5 Access Control
Multiple services can be defined in the **services** section, the access to each service is defined through the **access_roles** list.
```json
{
    "access_roles": [
        "api-test-token-08312"
    ]
}
```
Roles are defined through **api-access-tokens**.

### 6. Set up Similarity Search
```json
{
    "searches": [
        {
            "name": "portfolio_search",
            "definition": {
                "ref_retrieval": "portfolio_retrieval"
            },
            "access_roles": [
                "api-test-token-08312"
            ]
        }
    ]
}
```

### 7. Run as Services
#### 7.1 Start the api service as follows:
```shell
python ./src/api.py --def ./tutorial/def.json --env ./tutorial/app.env
```

##### 7.1.1 Submit request for chat response
```shell
curl --location 'http://127.0.0.1:8099/completion?sid=${session_id}' \
--header 'ctx-api-token: ${api-access-token}' --header 'Content-Type: application/json' \
--data '{ "user_query": "How to learn SQL programming?" }'
```

- The authentication is through the **api-access-token** which is provided and delivered by the server.
- A user is identified by the session ID (${session_id}), which must be a valid UUID.
- The session ID should remain consistent for a user and is independent from the session ID used by traditional web sessions.

##### 7.1.2 Submit request for similarity search:
```shell
curl --location 'http://127.0.0.1:8099/search?sid=${session_id}' \
--header 'ctx-api-token: ${api-access-token}' --header 'Content-Type: application/json' \
--data '{ "user_query": "How to learn SQL programming?", "search_kwargs: {"k": 30 }, "output_column": "news_id" }'
```

- **search_keywords** is optional and can be used to provide additional search constraints or improve search control.
- **output_column** is used when metadata needs to be returned. For example, when searching news articles by similarity using news_id, the news_id can be returned as metadata and then used to retrieve the full news content.

##### 7.1.3 Submit request for chat history:
```shell
curl --location 'http://127.0.0.1:8099/history?sid=${session_id}' \
--header 'ctx-api-token: ${api-access-token}' --header 'Content-Type: application/json'
```

- A chat history consists of user queries and AI responses.
- User queries are identified by the marker **`^~@^UM`**, and AI responses are identified by the marker **`^~@^AM`**.

**Please note that all service responses (chat, search & history) are returned in SSE (Server-Sent Events) format.**

#### 7.2 Run services in Docker container
- Build docker image
```shell
docker build -t qwshen/agentic-rag:1.0.0 .
```

- Run a container
```shell
docker run --name agentic-rag-1.0.0 -d --restart unless-stopped -e TZ=America/Toronto -v ~/Projects/agentic-rag/it-learning:/agentic-rag-1.0.0 -p 8089:8089 qwshen/agentic-rag:1.0.0
```
